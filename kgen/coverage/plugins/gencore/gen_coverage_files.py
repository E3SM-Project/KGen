
import os
import random
import json
from kgplugin import Kgen_Plugin
from parser import block_statements, statements, typedecl_statements
import collections

RECL = 10
META = 'metadata.json'

# TODO: gen_coverage subroutine should contains MPI communicator if MPI is enabled

class Gen_Coverage_File(Kgen_Plugin):
    def __init__(self):
        self.frame_msg = None
        self.paths = collections.OrderedDict()
        self.logger = getinfo('logger')

    def get_filepath(self, fileid):
        for filepath, (fid, lines) in self.paths.items():
            if fileid == fid:
                return str(filepath)

    def get_linepairs(self, fileid):
        for filepath, (fid, lines) in self.paths.items():
            if fileid == fid:
                return [ '"%s":"%s"'%(str(lineid), str(linenum)) for linenum, lineid in lines.items() ]

    def get_linenumbers(self, fileid):
        for filepath, (fid, lines) in self.paths.items():
            if fileid == fid:
                numbers = []
                for idx, linenum in enumerate(lines.keys()):
                    if idx != lines[linenum]:
                        raise Exception('Line number order mismatch.')
                    numbers.append( str(linenum) )
                return numbers

    def get_linenum(self, fileid, lineid):
        for filepath, (fid, lines) in self.paths.items():
            if fileid == fid:
                for linenum, lid in lines.items():
                    if lineid == lid:
                        return str(linenum)

    def append_path(self, node):
        if node.kgen_stmt.reader.id not in self.paths:
            node.kgen_stmt.top.genspair.used4coverage = True
            self.paths[node.kgen_stmt.reader.id] = ( len(self.paths), collections.OrderedDict() )

        lines = self.paths[node.kgen_stmt.reader.id][1]

        if node.kgen_stmt.item.span[1] not in lines:
            lines[node.kgen_stmt.item.span[1]] = len(lines)

    def add_stmt_block(self, node):
        if not self.ispure(node) and hasattr(node.kgen_stmt, 'unknowns'):
            path = self.paths[node.kgen_stmt.reader.id]
            if getinfo('is_mpi_app'):
                items = [ getinfo('mpi_comm'), str(path[0]), str(path[1][node.kgen_stmt.item.span[1]]) ]
            else:
                items = [ str(path[0]), str(path[1][node.kgen_stmt.item.span[1]]) ]
            attrs = {'designator': 'gen_coverage', 'items': items}
            part_insert_gensnode(node, EXEC_PART, statements.Call, index=0, attrs=attrs)

    def add_stmt(self, node):
        if not self.ispure(node) and hasattr(node.kgen_stmt, 'unknowns'):
            path = self.paths[node.kgen_stmt.reader.id]
            if getinfo('is_mpi_app'):
                items = [ getinfo('mpi_comm'), str(path[0]), str(path[1][node.kgen_stmt.item.span[1]]) ]
            else:
                items = [ str(path[0]), str(path[1][node.kgen_stmt.item.span[1]]) ]
            attrs = {'designator': 'gen_coverage', 'items': items}
            idx, name, part = get_part_index(node)
            part_insert_gensnode(node.kgen_parent, EXEC_PART, statements.Call, index=(idx+1), attrs=attrs)

    # registration
    def register(self, msg):

        self.frame_msg = msg

        # filepath idx, linenumber, mpi rank, openmp tid, time, counter, type id(invocation, papi l1 cache miss or elapsed time, ...)
        self.frame_msg.add_event(KERNEL_SELECTION.ALL, FILE_TYPE.STATE, GENERATION_STAGE.NODE_CREATED, \
            block_statements.IfThen, None, self.preprocess_ifthen)
        self.frame_msg.add_event(KERNEL_SELECTION.ALL, FILE_TYPE.STATE, GENERATION_STAGE.NODE_CREATED, \
            statements.ElseIf, None, self.preprocess_elseif)
        self.frame_msg.add_event(KERNEL_SELECTION.ALL, FILE_TYPE.STATE, GENERATION_STAGE.NODE_CREATED, \
            statements.Else, None, self.preprocess_else)
        self.frame_msg.add_event(KERNEL_SELECTION.ALL, FILE_TYPE.STATE, GENERATION_STAGE.NODE_CREATED, \
            statements.Case, None, self.preprocess_case)

        # when begin process
        self.frame_msg.add_event(KERNEL_SELECTION.ALL, FILE_TYPE.STATE, GENERATION_STAGE.BEGIN_PROCESS, \
            block_statements.IfThen, None, self.addstmt_ifthen)
        self.frame_msg.add_event(KERNEL_SELECTION.ALL, FILE_TYPE.STATE, GENERATION_STAGE.BEGIN_PROCESS, \
            statements.ElseIf, None, self.addstmt_elseif)
        self.frame_msg.add_event(KERNEL_SELECTION.ALL, FILE_TYPE.STATE, GENERATION_STAGE.BEGIN_PROCESS, \
            statements.Else, None, self.addstmt_else)
        self.frame_msg.add_event(KERNEL_SELECTION.ALL, FILE_TYPE.STATE, GENERATION_STAGE.BEGIN_PROCESS, \
            statements.Case, None, self.addstmt_case)
        self.frame_msg.add_event(KERNEL_SELECTION.ALL, FILE_TYPE.STATE, GENERATION_STAGE.BEGIN_PROCESS, \
            getinfo('topblock_stmt'), None, self.save_maps)

        # when finish process
        self.frame_msg.add_event(KERNEL_SELECTION.ALL, FILE_TYPE.STATE, GENERATION_STAGE.FINISH_PROCESS, \
            getinfo('topblock_stmt'), None, self.add_coverage)
        self.frame_msg.add_event(KERNEL_SELECTION.ALL, FILE_TYPE.STATE, GENERATION_STAGE.FINISH_PROCESS, \
            getinfo('topblock_stmt'), None, self.add_blockdata)
        self.frame_msg.add_event(KERNEL_SELECTION.ALL, FILE_TYPE.STATE, GENERATION_STAGE.FINISH_PROCESS, \
            getinfo('parentblock_stmt'), None, self.add_commonstmt)
        self.frame_msg.add_event(KERNEL_SELECTION.ALL, FILE_TYPE.STATE, GENERATION_STAGE.FINISH_PROCESS, \
            getinfo('callsite_stmts')[0], None, self.add_incinvoke)

    ##################################
    # preprocessing
    ##################################

    def preprocess_ifthen(self, node):
        #self.logger.debug('Begin preprocess_ifthen')
        covfilter = getinfo('coverage_filter')
        f2003 = node.kgen_stmt.f2003
        if covfilter is None or (hasattr(f2003, 'after_coverage') and f2003.after_coverage and \
            hasattr(f2003, 'coverage_name') and f2003.coverage_name in covfilter):
            self.append_path(node)

    def preprocess_elseif(self, node):
        #self.logger.debug('Begin preprocess_elseif')
        covfilter = getinfo('coverage_filter')
        f2003 = node.kgen_stmt.f2003
        if covfilter is None or (hasattr(f2003, 'after_coverage') and f2003.after_coverage and \
            hasattr(f2003, 'coverage_name') and f2003.coverage_name in covfilter):
            self.append_path(node)

    def preprocess_else(self, node):
        #self.logger.debug('Begin preprocess_else')
        covfilter = getinfo('coverage_filter')
        f2003 = node.kgen_stmt.f2003
        if covfilter is None or (hasattr(f2003, 'after_coverage') and f2003.after_coverage and \
            hasattr(f2003, 'coverage_name') and f2003.coverage_name in covfilter):
            self.append_path(node)

    def preprocess_case(self, node):
        #self.logger.debug('Begin preprocess_case')
        covfilter = getinfo('coverage_filter')
        f2003 = node.kgen_stmt.f2003
        if covfilter is None or (hasattr(f2003, 'after_coverage') and f2003.after_coverage and \
            hasattr(f2003, 'coverage_name') and f2003.coverage_name in covfilter):
            self.append_path(node)

    ##################################
    # printing paths
    ##################################

    def save_maps(self, node):

        # generate metadata.json for coverage
        if os.path.exists('%s/__data__/modeltypes'%getinfo('model_path')):
            json_data = None
            with open('%s/__data__/modeltypes'%getinfo('model_path'), 'r') as cm:
                json_data = json.load(cm)
                if u'"%s"'%getinfo('coverage_typeid') not in json_data[u'datamap']:
                    json_data[u'datamap'][u'"%s"'%getinfo('coverage_typeid')] = u'"%s"'%getinfo('coverage_typename')

            with open('%s/__data__/modeltypes'%getinfo('model_path'), 'w') as cm:
                cm.write(json.dumps(json_data))
        else:
            with open('%s/__data__/modeltypes'%getinfo('model_path'), 'w') as fm:
                fm.write(u'{"datatype": "model", "datamap": { "%s": "%s" }}\n'%\
                    (getinfo('coverage_typeid'), getinfo('coverage_typename')))

        # generate metadata.json for filemap
        with open('%s/__data__/%s/files'%(getinfo('model_path'), getinfo('coverage_typeid')), 'w') as fm:
            fm.write(u'{\n')
            files = []
            for fpath, (fid, lines) in self.paths.items():
                files.append(u'    "%d": "%s"'%(fid, fpath))
            fm.write(', \n'.join(files))
            fm.write(u'\n}')

        with open('%s/__data__/%s/lines'%(getinfo('model_path'), getinfo('coverage_typeid')), 'w') as fm:
            fm.write(u'{\n')
            lines = []
            for fileid in range(len(self.paths)):
                lines.append(u'    "%d": { %s }'%(fileid, ', '.join(self.get_linepairs(fileid))))
            fm.write(', \n'.join(lines))
            fm.write('\n}')

        #setinfo('coverage_paths', self.paths)

    ##################################
    # adding coverage statements
    ##################################

    def ispure(self, node):

        if hasattr(node, 'kgen_stmt') and node.kgen_stmt and \
            isinstance(node.kgen_stmt, block_statements.SubProgramStatement):        
            if node.kgen_stmt.is_pure() or node.kgen_stmt.is_elemental():
                return True

        if hasattr(node, 'kgen_parent'):
            return self.ispure(node.kgen_parent)

        return False

    def addstmt_ifthen(self, node):
        covfilter = getinfo('coverage_filter')
        f2003 = node.kgen_stmt.f2003
        if covfilter is None or (hasattr(f2003, 'after_coverage') and f2003.after_coverage and \
            hasattr(f2003, 'coverage_name') and f2003.coverage_name in covfilter):
            self.add_stmt_block(node)

    def addstmt_elseif(self, node):
        covfilter = getinfo('coverage_filter')
        f2003 = node.kgen_stmt.f2003
        if covfilter is None or (hasattr(f2003, 'after_coverage') and f2003.after_coverage and \
            hasattr(f2003, 'coverage_name') and f2003.coverage_name in covfilter):
            self.add_stmt(node)

    def addstmt_else(self, node):
        covfilter = getinfo('coverage_filter')
        f2003 = node.kgen_stmt.f2003
        if covfilter is None or (hasattr(f2003, 'after_coverage') and f2003.after_coverage and \
            hasattr(f2003, 'coverage_name') and f2003.coverage_name in covfilter):
            self.add_stmt(node)

    def addstmt_case(self, node):
        covfilter = getinfo('coverage_filter')
        f2003 = node.kgen_stmt.f2003
        if covfilter is None or (hasattr(f2003, 'after_coverage') and f2003.after_coverage and \
            hasattr(f2003, 'coverage_name') and f2003.coverage_name in covfilter):
            self.add_stmt(node)

    ##################################
    # adding  invoke increment statement
    ##################################

    def add_incinvoke(self, node):
        index, partname, part = get_part_index(node)

        if getinfo('is_openmp_app'):
            attrs = {'variable': 'kgen_invokes(OMP_GET_THREAD_NUM())', 'sign': '=', 'expr': 'kgen_invokes(OMP_GET_THREAD_NUM()) + 1'}
            part_insert_gensnode(node.kgen_parent, EXEC_PART, statements.Assignment, index=index, attrs=attrs)
        else:
            attrs = {'variable': 'kgen_invokes', 'sign': '=', 'expr': 'kgen_invokes + 1'}
            part_insert_gensnode(node.kgen_parent, EXEC_PART, statements.Assignment, index=index, attrs=attrs)


    ##################################
    # adding common statement
    ##################################

    def add_commonstmt(self, node):
        if getinfo('is_openmp_app'):
            attrs = {'type_spec': 'INTEGER', 'entity_decls': ['OMP_GET_THREAD_NUM']}
            part_append_gensnode(node, DECL_PART, typedecl_statements.Integer, attrs=attrs)

            attrs = {'type_spec': 'INTEGER', 'attrspec': [ 'DIMENSION(0:%d)'%(getinfo('openmp_maxthreads')-1) ], 'entity_decls': ['kgen_invokes']}
            part_append_gensnode(node, DECL_PART, typedecl_statements.Integer, attrs=attrs)

        else:
            attrs = {'type_spec': 'INTEGER', 'entity_decls': ['kgen_invokes']}
            part_append_gensnode(node, DECL_PART, typedecl_statements.Integer, attrs=attrs)

        attrs = {'items': [ ( 'state', ('kgen_invokes', ) ) ]}
        part_append_gensnode(node, DECL_PART, statements.Common, attrs=attrs)

    ##################################
    # adding common block data
    ##################################

    def add_blockdata(self, node):

        part_append_comment(node.kgen_parent, UNIT_PART, '')

        attrs = {'name': 'KGEN'}
        cblock = part_append_gensnode(node.kgen_parent, UNIT_PART, block_statements.BlockData, attrs=attrs)

        if getinfo('is_openmp_app'):
            attrs = {'type_spec': 'INTEGER', 'attrspec': [ 'DIMENSION(0:%d)'%(getinfo('openmp_maxthreads')-1) ], 'entity_decls': ['kgen_invokes = 0']}
            part_append_gensnode(cblock, DECL_PART, typedecl_statements.Integer, attrs=attrs)
        else:
            attrs = {'type_spec': 'INTEGER', 'entity_decls': ['kgen_invokes = 0']}
            part_append_gensnode(cblock, DECL_PART, typedecl_statements.Integer, attrs=attrs)

        attrs = {'items': [ ( 'state', ('kgen_invokes',) ) ]}
        part_append_gensnode(cblock, DECL_PART, statements.Common, attrs=attrs)


    ##################################
    # adding coverage subroutine
    ##################################

    def add_coverage(self, node):
        #self.logger.debug('Begin add_coverage')

        if len(self.paths) == 0:
            self.logger.warn('There is no valid conditional block.')
            return

        maxlines = max([ len(lineids) for fileid, lineids in self.paths.values() ])

        part_append_comment(node.kgen_parent, UNIT_PART, '')

        # add subroutine
        if getinfo('is_mpi_app'):
            attrs = {'name': 'gen_coverage', 'args': ['mpicomm', 'fileid', 'lineid']}
        else:
            attrs = {'name': 'gen_coverage', 'args': ['fileid', 'lineid']}
        coversubr = part_append_gensnode(node.kgen_parent, UNIT_PART, block_statements.Subroutine, attrs=attrs)

        part_append_comment(coversubr, DECL_PART, '')

        attrs = {'type_spec': 'CHARACTER', 'selector':('4096', None), 'entity_decls': ['datapath']}
        part_append_gensnode(coversubr, DECL_PART, typedecl_statements.Character, attrs=attrs)

        attrs = {'type_spec': 'CHARACTER', 'selector':('6', None), 'entity_decls': ['filestr']}
        part_append_gensnode(coversubr, DECL_PART, typedecl_statements.Character, attrs=attrs)

        attrs = {'type_spec': 'CHARACTER', 'selector':('6', None), 'entity_decls': ['linestr']}
        part_append_gensnode(coversubr, DECL_PART, typedecl_statements.Character, attrs=attrs)

        attrs = {'type_spec': 'CHARACTER', 'selector':('10', None), 'entity_decls': ['rankstr']}
        part_append_gensnode(coversubr, DECL_PART, typedecl_statements.Character, attrs=attrs)

        attrs = {'type_spec': 'CHARACTER', 'selector':('6', None), 'entity_decls': ['threadstr']}
        part_append_gensnode(coversubr, DECL_PART, typedecl_statements.Character, attrs=attrs)

        attrs = {'type_spec': 'CHARACTER', 'selector':('1', None), 'entity_decls': ['dummychar']}
        part_append_gensnode(coversubr, DECL_PART, typedecl_statements.Character, attrs=attrs)

        attrs = {'type_spec': 'INTEGER', 'entity_decls': [ 'ierror']}
        part_append_gensnode(coversubr, DECL_PART, typedecl_statements.Integer, attrs=attrs)

        if getinfo('is_mpi_app'):

            for mod_name, use_names in getinfo('mpi_use'):
                attrs = {'name':mod_name, 'isonly': True, 'items':use_names}
                part_append_gensnode(coversubr, USE_PART, statements.Use, attrs=attrs)

            attrs = {'type_spec': 'LOGICAL', 'attrspec': [ 'SAVE' ], 'entity_decls': ['kgen_initialized = .FALSE.']}
            part_append_gensnode(coversubr, DECL_PART, typedecl_statements.Logical, attrs=attrs)

            attrs = {'type_spec': 'INTEGER', 'entity_decls': ['myrank', 'numranks']}
            part_append_gensnode(coversubr, DECL_PART, typedecl_statements.Integer, attrs=attrs)

            attrs = {'type_spec': 'INTEGER', 'attrspec': [ 'INTENT(IN)' ], 'entity_decls': ['mpicomm']}
            part_append_gensnode(coversubr, DECL_PART, typedecl_statements.Integer, attrs=attrs)

        attrs = {'type_spec': 'CHARACTER', 'selector':('10', None), 'entity_decls': ['numranksstr']}
        part_append_gensnode(coversubr, DECL_PART, typedecl_statements.Character, attrs=attrs)

        if getinfo('is_openmp_app'):
            attrs = {'type_spec': 'INTEGER', 'entity_decls': ['OMP_GET_THREAD_NUM', 'OMP_GET_NUM_THREADS']}
            part_append_gensnode(coversubr, DECL_PART, typedecl_statements.Integer, attrs=attrs)

            attrs = {'type_spec': 'INTEGER', 'attrspec': [ 'DIMENSION(0:%d)'%(getinfo('openmp_maxthreads')-1) ], 'entity_decls': ['kgen_invokes']}
            part_append_gensnode(coversubr, DECL_PART, typedecl_statements.Integer, attrs=attrs)

        else:
            attrs = {'type_spec': 'INTEGER', 'entity_decls': ['kgen_invokes']}
            part_append_gensnode(coversubr, DECL_PART, typedecl_statements.Integer, attrs=attrs)

        attrs = {'type_spec': 'CHARACTER', 'selector':('6', None), 'entity_decls': ['numthreadsstr']}
        part_append_gensnode(coversubr, DECL_PART, typedecl_statements.Character, attrs=attrs)

        attrs = {'type_spec': 'INTEGER', 'entity_decls': [ 'invokes', 'visits', 'intnum' ]}
        part_append_gensnode(coversubr, DECL_PART, typedecl_statements.Integer, attrs=attrs)

        attrs = {'type_spec': 'INTEGER', 'entity_decls': ['mpiunit', 'ompunit', 'dataunit']}
        part_append_gensnode(coversubr, DECL_PART, typedecl_statements.Integer, attrs=attrs)

        attrs = {'type_spec': 'LOGICAL', 'entity_decls': ['istrue']}
        part_append_gensnode(coversubr, DECL_PART, typedecl_statements.Logical, attrs=attrs)

        attrs = {'type_spec': 'INTEGER', 'attrspec': ['INTENT(IN)'], 'entity_decls': ['fileid', 'lineid']}
        part_append_gensnode(coversubr, DECL_PART, typedecl_statements.Integer, attrs=attrs)

        attrs = {'items': [ ( 'state', ('kgen_invokes', ) ) ]}
        part_append_gensnode(coversubr, DECL_PART, statements.Common, attrs=attrs)

        part_append_comment(coversubr, DECL_PART, '')

        ############# exec_part ########################

        datapath = '%s/__data__'%getinfo('model_path')
        codepath = '%s/%s'%(datapath, getinfo('coverage_typeid'))

        if getinfo('is_openmp_app'):
            part_append_comment(coversubr, EXEC_PART, 'CRITICAL (kgen_cover)', style='openmp')

        attrs = {'specs': [ 'filestr', '"(I6)"' ], 'items': [ 'fileid' ]}
        part_append_gensnode(coversubr, EXEC_PART, statements.Write, attrs=attrs)

        attrs = {'specs': [ 'linestr', '"(I6)"' ], 'items': [ 'lineid' ]}
        part_append_gensnode(coversubr, EXEC_PART, statements.Write, attrs=attrs)

        topobj = coversubr

        if getinfo('is_mpi_app'):

            attrs = {'designator': 'MPI_INITIALIZED', 'items': [ 'kgen_initialized', 'ierror' ]}
            part_append_gensnode(topobj, EXEC_PART, statements.Call, attrs=attrs)

            attrs = {'expr': 'kgen_initialized .AND. ( ierror .EQ. MPI_SUCCESS )'}
            topobj = part_append_gensnode(topobj, EXEC_PART, block_statements.IfThen, attrs=attrs)

            attrs = {'designator': 'MPI_COMM_RANK', 'items': [ 'mpicomm', 'myrank', 'ierror' ]}
            part_append_gensnode(topobj, EXEC_PART, statements.Call, attrs=attrs)

            attrs = {'specs': [ 'rankstr', '"(I10)"' ], 'items': [ 'myrank' ]}
            part_append_gensnode(topobj, EXEC_PART, statements.Write, attrs=attrs)
        else:
            attrs = {'specs': [ 'rankstr', '"(I1)"' ], 'items': [ '0' ]}
            part_append_gensnode(topobj, EXEC_PART, statements.Write, attrs=attrs)

        if getinfo('is_openmp_app'):
            attrs = {'specs': [ 'threadstr', '"(I6)"' ], 'items': [ 'OMP_GET_THREAD_NUM()' ]}
            part_append_gensnode(topobj, EXEC_PART, statements.Write, attrs=attrs)
        else:
            attrs = {'specs': [ 'threadstr', '"(I1)"' ], 'items': [ '0' ]}
            part_append_gensnode(topobj, EXEC_PART, statements.Write, attrs=attrs)

        # nummpiranks
        attrs = {'specs': ['FILE="%s/mpi"'%codepath, 'EXIST=istrue']}
        part_append_gensnode(topobj, EXEC_PART, statements.Inquire, attrs=attrs)

        attrs = {'expr': '.NOT. istrue'}
        ifnotmpi = part_append_gensnode(topobj, EXEC_PART, block_statements.IfThen, attrs=attrs)

        if getinfo('is_mpi_app'):

            attrs = {'designator': 'MPI_COMM_SIZE', 'items': [ 'mpicomm', 'numranks', 'ierror' ]}
            part_append_gensnode(ifnotmpi, EXEC_PART, statements.Call, attrs=attrs)

            attrs = {'specs': [ 'numranksstr', '"(I10)"' ], 'items': [ 'numranks' ]}
            part_append_gensnode(ifnotmpi, EXEC_PART, statements.Write, attrs=attrs)

        else:
            attrs = {'specs': [ 'numranksstr', '"(I10)"' ], 'items': [ '1' ]}
            part_append_gensnode(ifnotmpi, EXEC_PART, statements.Write, attrs=attrs)

        attrs = {'specs': ['NEWUNIT=mpiunit', 'FILE="%s/mpi"'%codepath, \
            'STATUS="NEW"', 'ACTION="WRITE"', 'FORM="FORMATTED"', 'IOSTAT=ierror']}
        part_append_gensnode(ifnotmpi, EXEC_PART, statements.Open, attrs=attrs)

        attrs = {'expr': 'ierror .EQ. 0'}
        ifmpiopen = part_append_gensnode(ifnotmpi, EXEC_PART, block_statements.IfThen, attrs=attrs)

        attrs = {'specs': [ 'UNIT=mpiunit', 'FMT="(A)"' ], 'items': [ 'TRIM(ADJUSTL(numranksstr))' ]}
        part_append_gensnode(ifmpiopen, EXEC_PART, statements.Write, attrs=attrs)

        attrs = {'specs': ['UNIT=mpiunit']}
        part_append_gensnode(ifmpiopen, EXEC_PART, statements.Close, attrs=attrs)

        # numopenmpthreads
        attrs = {'specs': ['FILE="%s/openmp"'%codepath, 'EXIST=istrue']}
        part_append_gensnode(topobj, EXEC_PART, statements.Inquire, attrs=attrs)

        attrs = {'expr': '.NOT. istrue'}
        ifnotomp = part_append_gensnode(topobj, EXEC_PART, block_statements.IfThen, attrs=attrs)

        if getinfo('is_openmp_app'):
            attrs = {'specs': [ 'numthreadsstr', '"(I6)"' ], 'items': [ 'OMP_GET_NUM_THREADS()' ]}
            part_append_gensnode(ifnotomp, EXEC_PART, statements.Write, attrs=attrs)
        else:
            attrs = {'specs': [ 'numthreadsstr', '"(I1)"' ], 'items': [ '1' ]}
            part_append_gensnode(ifnotomp, EXEC_PART, statements.Write, attrs=attrs)

        attrs = {'specs': ['NEWUNIT=ompunit', 'FILE="%s/openmp"'%codepath, \
            'STATUS="NEW"', 'ACTION="WRITE"', 'FORM="FORMATTED"', 'IOSTAT=ierror']}
        part_append_gensnode(ifnotomp, EXEC_PART, statements.Open, attrs=attrs)

        attrs = {'expr': 'ierror .EQ. 0'}
        ifompopen = part_append_gensnode(ifnotomp, EXEC_PART, block_statements.IfThen, attrs=attrs)

        attrs = {'specs': [ 'UNIT=ompunit', 'FMT="(A)"' ], 'items': [ 'TRIM(ADJUSTL(numthreadsstr))' ]}
        part_append_gensnode(ifompopen, EXEC_PART, statements.Write, attrs=attrs)

        attrs = {'specs': ['UNIT=ompunit']}
        part_append_gensnode(ifompopen, EXEC_PART, statements.Close, attrs=attrs)

        # create data directory
        attrs = {'specs': [ 'datapath', '*' ], 'items': [ '"%s/" // TRIM(ADJUSTL(rankstr)) // "/" // TRIM(ADJUSTL(threadstr))'%codepath ]}
        part_append_gensnode(topobj, EXEC_PART, statements.Write, attrs=attrs)

        attrs = {'specs': ['FILE=TRIM(ADJUSTL(datapath)) // "/" // TRIM(ADJUSTL(filestr)) // "." // TRIM(ADJUSTL(linestr))', 'EXIST=istrue']}
        part_append_gensnode(topobj, EXEC_PART, statements.Inquire, attrs=attrs)

        attrs = {'expr': 'istrue'}
        ifexist = part_append_gensnode(topobj, EXEC_PART, block_statements.IfThen, attrs=attrs)

        attrs = {'specs': ['NEWUNIT=dataunit', 'FILE=TRIM(ADJUSTL(datapath)) // "/" // TRIM(ADJUSTL(filestr)) // "." // TRIM(ADJUSTL(linestr))', \
            'STATUS="OLD"', 'ACTION="READWRITE"', 'FORM="FORMATTED"', 'ACCESS="DIRECT"', 'RECL=33', 'IOSTAT=ierror']}
        part_append_gensnode(ifexist, EXEC_PART, statements.Open, attrs=attrs)

        attrs = {'expr': 'ierror .EQ. 0'}
        ifopen = part_append_gensnode(ifexist, EXEC_PART, block_statements.IfThen, attrs=attrs)

        attrs = {'specs': ['UNIT=dataunit', 'SIZE=intnum']}
        part_append_gensnode(ifopen, EXEC_PART, statements.Inquire, attrs=attrs)

        attrs = {'specs': [ 'UNIT=dataunit', 'REC=intnum/33', 'FMT="(2I16,1A)"' ], 'items': [ 'invokes', 'visits', 'dummychar' ]}
        part_append_gensnode(ifopen, EXEC_PART, statements.Read, attrs=attrs)

        if getinfo('is_openmp_app'):
            attrs = {'expr': 'invokes .EQ. kgen_invokes(OMP_GET_THREAD_NUM())'}
        else:
            attrs = {'expr': 'invokes .EQ. kgen_invokes'}
        ifmatch = part_append_gensnode(ifopen, EXEC_PART, block_statements.IfThen, attrs=attrs)

        attrs = {'variable': 'visits', 'sign': '=', 'expr': 'visits + 1'}
        part_append_gensnode(ifmatch, EXEC_PART, statements.Assignment, attrs=attrs)

        attrs = {'specs': [ 'UNIT=dataunit', 'REC=intnum/33', 'FMT="(2I16,1A)"' ], 'items': [ 'invokes', 'visits', 'NEW_LINE("A")']}
        part_append_gensnode(ifmatch, EXEC_PART, statements.Write, attrs=attrs)

        part_append_gensnode(ifmatch, EXEC_PART, statements.Else)

        if getinfo('is_openmp_app'):
            attrs = {'specs': [ 'UNIT=dataunit', 'REC=(intnum/33+1)', 'FMT="(2I16,1A)"' ], 'items': [ 'kgen_invokes(OMP_GET_THREAD_NUM())', '1', 'NEW_LINE("A")' ]}
        else:
            attrs = {'specs': [ 'UNIT=dataunit', 'REC=(intnum/33+1)', 'FMT="(2I16,1A)"' ], 'items': [ 'kgen_invokes', '1', 'NEW_LINE("A")' ]}
        part_append_gensnode(ifmatch, EXEC_PART, statements.Write, attrs=attrs)

        attrs = {'specs': ['UNIT=dataunit']}
        part_append_gensnode(ifopen, EXEC_PART, statements.Close, attrs=attrs)

        part_append_gensnode(ifexist, EXEC_PART, statements.Else)

        attrs = {'specs': ['NEWUNIT=dataunit', 'FILE=TRIM(ADJUSTL(datapath)) // "/" // TRIM(ADJUSTL(filestr)) // "." // TRIM(ADJUSTL(linestr))', \
            'STATUS="NEW"', 'ACTION="READWRITE"', 'FORM="FORMATTED"', 'ACCESS="DIRECT"', 'RECL=33', 'IOSTAT=ierror']}
        part_append_gensnode(ifexist, EXEC_PART, statements.Open, attrs=attrs)

        attrs = {'expr': 'ierror .NE. 0'}
        ifnotexist = part_append_gensnode(ifexist, EXEC_PART, block_statements.IfThen, attrs=attrs)
 
        attrs = {'designator': 'SYSTEM', 'items': [ '"mkdir -p " // TRIM(ADJUSTL(datapath))']}
        part_append_gensnode(ifnotexist, EXEC_PART, statements.Call, attrs=attrs)

        attrs = {'specs': ['NEWUNIT=dataunit', 'FILE=TRIM(ADJUSTL(datapath)) // "/" // TRIM(ADJUSTL(filestr)) // "." // TRIM(ADJUSTL(linestr))', \
            'STATUS="NEW"', 'ACTION="READWRITE"', 'FORM="FORMATTED"', 'ACCESS="DIRECT"', 'RECL=33', 'IOSTAT=ierror']}
        part_append_gensnode(ifnotexist, EXEC_PART, statements.Open, attrs=attrs)

        attrs = {'expr': 'ierror .EQ. 0'}
        ifnewexist = part_append_gensnode(ifexist, EXEC_PART, block_statements.IfThen, attrs=attrs)

        if getinfo('is_openmp_app'):
            attrs = {'specs': [ 'UNIT=dataunit', 'REC=1', 'FMT="(2I16,1A)"' ], 'items': [ 'kgen_invokes(OMP_GET_THREAD_NUM())', '1', 'NEW_LINE("A")' ]}
        else:
            attrs = {'specs': [ 'UNIT=dataunit', 'REC=1', 'FMT="(2I16,1A)"' ], 'items': [ 'kgen_invokes', '1', 'NEW_LINE("A")' ]}
        part_append_gensnode(ifnewexist, EXEC_PART, statements.Write, attrs=attrs)

        attrs = {'specs': ['UNIT=dataunit']}
        part_append_gensnode(ifnewexist, EXEC_PART, statements.Close, attrs=attrs)

        if getinfo('is_openmp_app'):
            part_append_comment(coversubr, EXEC_PART, 'END CRITICAL (kgen_cover)', style='openmp')

        part_append_comment(coversubr, EXEC_PART, '')

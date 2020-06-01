'''Compiler flag detection
'''

import os
import stat
import shutil
import subprocess
import kgtool
import kgutils
import kgcompiler
from kgconfig import Config
try:
    import configparser
except:
    import ConfigParser as configparser

STR_EX = 'execve('
STR_EN = 'ENOENT'
STR_UF = '<unfinished'
STR_RE = 'resumed>'
#TEMP_SH = '#!/bin/bash\n%s\n%s\n%s\n'
#SH = '%s/_kgen_compflag_cmdwrapper.sh'

class CompFlag(kgtool.KGTool):

    def run(self):

        # build app.
        stracepath = os.path.join(Config.path['outdir'], Config.stracefile)
        includepath = os.path.join(Config.path['outdir'], Config.includefile)
        tmpsrcdir = os.path.abspath(os.path.join(Config.path['outdir'], Config.path['tmpsrcdir']))

        #if not os.path.exists(stracepath) or 'all' in Config.rebuild or 'strace' in Config.rebuild:
        if not os.path.exists(includepath) or 'all' in Config.rebuild or 'include' in Config.rebuild:

            # clean app.
            if Config.cmd_clean['cmds']:
                kgutils.run_shcmd(Config.cmd_clean['cmds'])
            if Config.state_switch['clean']:
                kgutils.run_shcmd(Config.state_switch['clean'])

            #with open(SH%Config.cwd, 'w') as f:
            #    f.write(TEMP_SH%(Config.cmd_clean['cmds'], Config.prerun['build'], Config.cmd_build['cmds']))
            #st = os.stat(SH%Config.cwd)
            #os.chmod(SH%Config.cwd, st.st_mode | stat.S_IEXEC)
        
            # include 
            cfg = configparser.RawConfigParser()
            cfg.optionxform = str

            if len(Config.include['path'])>0:
                cfg.add_section('include')
                for inc in Config.include['path']:
                    for i in inc.split(':'):
                        cfg.set('include', i, '')

            if len(Config.include['macro'])>0:
                cfg.add_section('macro')
                for key, value in Config.include['macro'].items():
                    cfg.set('macro', key, value)

            if len(Config.include['import'])>0:
                cfg.add_section('import')
                for key, value in Config.include['macro'].items():
                    cfg.set('import', key, value)

            if Config.prerun['build']:
                cmdstr = '%s;%s'%(Config.prerun['build'], Config.cmd_build['cmds'])
            else:
                cmdstr = Config.cmd_build['cmds']

            kgutils.logger.info('Collecting strace log')

            #bld_cmd = 'strace -o %s -f -q -s 100000 -e trace=execve -v -- /bin/sh -c "%s"'%(stracepath, cmdstr)
            bld_cmd = 'strace -f -q -s 100000 -e trace=execve -v -- /bin/sh -c "%s"'% cmdstr

            try:

                if not os.path.exists(tmpsrcdir):
                    os.makedirs(tmpsrcdir)

                tmpsrcid = 0

                flags = {}

                process = subprocess.Popen(bld_cmd, stdin=subprocess.PIPE, \
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, \
                            shell=True)

                while True:

                    #line = process.stdout.readline()
                    line = process.stderr.readline()

                    if line == '' and process.poll() is not None:
                        break

                    if line:

                        pos_execve = line.find(STR_EX)
                        if pos_execve >= 0:
                            pos_enoent = line.rfind(STR_EN)
                            if pos_enoent < 0:
                                pos_last = line.rfind(STR_UF)
                                if pos_last < 0:
                                    pos_last = line.rfind(']')
                                else:
                                    pos_last -= 1
                                if pos_last >= 0:
                                    try:
                                        exec('exepath, cmdlist, env = %s'%line[pos_execve+len(STR_EX):(pos_last+1)])
                                        compid = cmdlist[0].split('/')[-1]
                                        if exepath and cmdlist and compid==cmdlist[0].split('/')[-1]:
                                            compiler = kgcompiler.CompilerFactory.createCompiler(compid)
                                            if compiler:
                                                srcs, incs, macros, openmp, options = compiler.parse_option(cmdlist, self._getpwd(env))
                                                if len(srcs)>0:
                                                    for src in srcs:

                                                        #if src not in flags:
                                                        #    flags[src] = [ (exepath, incs, macros, openmp, options, tmpsrc) ]

                                                        #    if os.path.isfile(src):
                                                        #        shutil.copyfile(src, os.path.join(tmpsrc))

                                                        if src in flags:
                                                            #tmpsrc = flags[src][0][5]
                                                            #flags[src].append((exepath, incs, macros, openmp, options, tmpsrc))

                                                            flags[src].append((exepath, incs, macros, openmp, options))

                                                        else:
                                                            #tmpsrc = os.path.join(tmpsrcdir, str(tmpsrcid))

                                                            #flags[src] = [ (exepath, incs, macros, openmp, options, tmpsrc) ]
                                                            flags[src] = [ (exepath, incs, macros, openmp, options) ]

                                                            # cp file to tmpsrcdir
                                                            if os.path.isfile(src):
                                                                #shutil.copyfile(src, os.path.join(tmpsrc))
                                                                tmpsrcid += 1
                                    except Exception as err:
                                        raise
                                        pass

                # get return code
                retcode = process.poll()

                for fname, incitems in flags.items():
                    if len(incitems)>0:
                        # save the last compiler set
                        compiler = incitems[-1][0]
                        incs = incitems[-1][1]
                        macros = incitems[-1][2]
                        options = incitems[-1][4]
                        #tmpsrcid = incitems[-1][5]

                        if cfg.has_section(fname):
                            print 'Warning: %s section is dupulicated.' % fname
                        else:
                            cfg.add_section(fname)
                            #cfg.set(fname,'tmpsrcid', tmpsrcid)
                            cfg.set(fname,'compiler', compiler)
                            cfg.set(fname,'compiler_options', ' '.join(options))
                            cfg.set(fname,'include',':'.join(incs))
                            for name, value in macros:
                                cfg.set(fname, name, value)

                if len(cfg.sections())>0:
                    with open(includepath, 'w') as f:
                        cfg.write(f)

                #out, err, retcode = kgutils.run_shcmd(bld_cmd)
                if retcode != 0 and os.path.exists(stracepath):
                    os.remove(stracepath)
                    kgutils.logger.error('%s\n%s'%(err, out))
            except Exception as err:
                if os.path.exists(stracepath):
                    os.remove(stracepath)
                #import pdb; pdb.set_trace()
                #kgutils.logger.error('%s\n%s'%(err, out))
                raise
        else:
            kgutils.logger.info('Reusing KGen include file: %s'%includepath)


    def _getpwd(self, env):
        for item in env:
            if item.startswith('PWD='):
                return item[4:]
        return None

#    def _geninclude(self, stracepath, includepath):
#
#        kgutils.logger.info('Creating KGen include file: %s'%includepath)
#
#        cfg = configparser.RawConfigParser()
#        cfg.optionxform = str
#
#        if len(Config.include['path'])>0:
#            cfg.add_section('include')
#            for inc in Config.include['path']:
#                for i in inc.split(':'):
#                    cfg.set('include', i, '')
#
#        if len(Config.include['macro'])>0:
#            cfg.add_section('macro')
#            for key, value in Config.include['macro'].items():
#                cfg.set('macro', key, value)
#
#        if len(Config.include['import'])>0:
#            cfg.add_section('import')
#            for key, value in Config.include['macro'].items():
#                cfg.set('import', key, value)
#
#
#        if not os.path.exists(stracepath):
#            raise Exception('No strace file is found.')
#
#        flags = {}
#        with open(stracepath, 'r') as f:
#            line = f.readline()
#            while(line):
#                pos_execve = line.find(STR_EX)
#                if pos_execve >= 0:
#                    pos_enoent = line.rfind(STR_EN)
#                    if pos_enoent < 0:
#                        pos_last = line.rfind(STR_UF)
#                        if pos_last < 0:
#                            pos_last = line.rfind(']')
#                        else:
#                            pos_last -= 1
#                        if pos_last >= 0:
#                            try:
#                                exec('exepath, cmdlist, env = %s'%line[pos_execve+len(STR_EX):(pos_last+1)])
#                                compid = cmdlist[0].split('/')[-1]
#                                if exepath and cmdlist and compid==cmdlist[0].split('/')[-1]:
#                                    compiler = kgcompiler.CompilerFactory.createCompiler(compid)
#                                    if compiler:
#                                        srcs, incs, macros, openmp, options = compiler.parse_option(cmdlist, self._getpwd(env))
#                                        if len(srcs)>0:
#                                            for src in srcs:
#                                                if src in flags:
#                                                    flags[src].append((exepath, incs, macros, openmp, options))
#                                                else:
#                                                    flags[src] = [ (exepath, incs, macros, openmp, options) ]
#                            except Exception as err:
#                                raise
#                                pass
#                line = f.readline()
#
#        for fname, incitems in flags.items():
#            if len(incitems)>0:
#                # save the last compiler set
#                compiler = incitems[-1][0]
#                incs = incitems[-1][1]
#                macros = incitems[-1][2]
#                options = incitems[-1][4]
#
#                if cfg.has_section(fname):
#                    print 'Warning: %s section is dupulicated.' % fname
#                else:
#                    cfg.add_section(fname)
#                    cfg.set(fname,'compiler', compiler)
#                    cfg.set(fname,'compiler_options', ' '.join(options))
#                    cfg.set(fname,'include',':'.join(incs))
#                    for name, value in macros:
#                        cfg.set(fname, name, value)
#
#        if len(cfg.sections())>0:
#            with open(includepath, 'w') as f:
#                cfg.write(f)
#

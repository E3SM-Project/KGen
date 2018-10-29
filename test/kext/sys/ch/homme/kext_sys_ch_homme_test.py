# kgentest.py

import os
import shutil
import re
import time
from kgutils import run_shcmd
from kext_sys_ch_test import KExtSysCHTest

class KExtSysCHHommeTest(KExtSysCHTest):

    def download(self, myname, result):

        systestdir = result['mkdir_task']['sysdir']
        workdir = result['mkdir_task']['workdir']

        appsrc = '%s/homme_ref'%systestdir
        if not os.path.exists(appsrc):
            os.mkdir(appsrc)

        # check if homme exists in appsrc dir
        out, err, retcode = run_shcmd('svn info | grep URL', cwd=appsrc)
        if retcode != 0 or not out or len(out)<3 or not out.startswith('URL'):
            out, err, retcode = run_shcmd('svn checkout -r 5798 https://svn-homme-model.cgd.ucar.edu/trunk/ .', cwd=appsrc)

        # copy homme src into test specific src dir
        tmpsrc = '%s/homme_work'%systestdir
#        if os.path.exists(tmpsrc):
#            shutil.rmtree(tmpsrc)
#        shutil.copytree(appsrc, tmpsrc)
        if not os.path.exists(tmpsrc):
            shutil.copytree(appsrc, tmpsrc)
        else:
            for fname in os.listdir('%s/src'%tmpsrc):
                if fname.endswith('.kgen'):
                    shutil.copyfile(os.path.join('%s/src'%tmpsrc, fname), os.path.join('%s/src'%tmpsrc, fname[:-5]))
            for fname in os.listdir('%s/src/share'%tmpsrc):
                if fname.endswith('.kgen'):
                    shutil.copyfile(os.path.join('%s/src/share'%tmpsrc, fname), os.path.join('%s/src/share'%tmpsrc, fname[:-5]))

        result[myname]['appsrc'] = appsrc
        result[myname]['tmpsrc'] = tmpsrc

        self.set_status(result, myname, self.PASSED)

        return result

#    def build(self, myname, result):
#
#        statefiles = result['generate_task']['statefiles']
#        workdir = result['mkdir_task']['workdir']
#        blddir = result['config_task']['blddir'] 
#        prerun_cmds = result['config_task']['prerun_build'] 
#
#        datadir = '%s/data'%workdir
#        result[myname]['datadir'] = datadir
#
#        if self.REBUILD or not os.path.exists(datadir) or any(not os.path.exists('%s/%s'%(datadir, sf)) for sf in statefiles):
#            if self.LEAVE_TEMP:
#                with open('%s/build_cmds.sh'%blddir, 'w') as f:
#                    f.write('#!/bin/bash\n')
#                    f.write('\n')
#                    for cmd in prerun_cmds:
#                        f.write('    %s\n'%cmd)
#                    f.write('    make clean\n')
#                    f.write('    make -j 4 perfTest &> build.log')
#                os.chmod('%s/build_cmds.sh'%blddir, 0755)
#
#            # build
#            out, err, retcode = self.run_shcmd('%s; make clean; make -j 8 perfTest &> build.log'%'; '.join(prerun_cmds), cwd=blddir)
#            if retcode != 0:
#                self.set_status(result, myname, self.FAILED, errmsg='Homme build is failed.')
#            else:
#                self.set_status(result, myname, self.PASSED)
#        else:
#            # copy files from data to kernel directory
#            for statefile in statefiles:
#                shutil.copyfile(os.path.join(datadir, statefile), '%s/kernel/%s'%(workdir, statefile))
#
#            if os.path.exists(os.path.join(datadir, 'kgen_statefile.lst')):
#                shutil.copyfile(os.path.join(datadir, 'kgen_statefile.lst'), '%s/kernel/kgen_statefile.lst'%workdir)
#
#            result['goto'] = 'runkernel_task'
#            self.set_status(result, myname, self.PASSED)
#
#        return result
#
#    def genstate(self, myname, result):
#
#        workdir = result['mkdir_task']['workdir']
#        tmpsrc = result['download_task']['tmpsrc']
#        blddir = result['config_task']['blddir']
#        prerun_cmds = result['config_task']['prerun_run'] 
#        mpirun = result['config_task']['mpirun'] 
#
#        rundir = '%s/run'%workdir
#        if os.path.exists(rundir):
#            shutil.rmtree(rundir)
#        os.mkdir(rundir)
#        os.mkdir('%s/movies'%rundir)
#        result[myname]['rundir'] = rundir
#        
#        # may need to add -P BSUB directive in .run and .st_archive scripts
#
#        # prepare namelist
#        params = {'nelem': '6', 'nth': '2', 'nath': '2', 'tstep': '360'}
#        if os.path.exists('%s/homme.nl'%rundir): os.system('rm -f %s/homme.nl'%rundir)
#        with open('%s/homme.nl'%rundir, 'w') as fd:
#            fd.write(namelist%params)
#
#        # create symbolic linke to input data
#        if os.path.exists('%s/vcoord'%rundir): os.system('unlink %s/vcoord'%rundir)
#        os.system('ln -s %s/test/vcoord %s/vcoord'%(tmpsrc, rundir))
#
#        os.system('rm -f %s/homme.*.err'%rundir)
#        os.system('rm -f %s/homme.*.out'%rundir)
#
#        # create job submit script
#        with open('%s/homme.submit'%rundir, 'w') as fd:
#            fd.write(job_script%('16', '16', '\n'.join(prerun_cmds), mpirun, '%s/test_execs/perfTest/perfTest'%blddir, '%s/homme.nl'%rundir))
#
#
#        # submit and wait to finish
#        out, err, retcode = self.run_shcmd('bsub < homme.submit', cwd=rundir)
#
#        if retcode != 0 or not out:
#            self.set_status(result, myname, self.FAILED, errmsg='Job submission is failed.')
#            return result
#
#        # find jobid
#        jobid = None
#        for iter in range(120):
#            time.sleep(5)
#            out, err, retcode = self.run_shcmd('bjobs')
#            for line in out.split('\n'):
#                items = line.split()
#                if len(items)>6 and items[6].endswith('KHOMME'):
#                    jobid = items[0]
#                    break
#            if jobid: break
#
#        if jobid is None:
#            self.set_status(result, myname, self.FAILED, errmsg='Job id is not found.')
#            return result
#
#        status = ''
#        maxiter = 3600
#        iter = 0
#        while status not in [ 'DONE', 'PSUSP', 'USUSP', 'SSUSP', 'EXIT', 'UNKWN', 'ZOMBI', 'FINISHED' ]:
#            time.sleep(1)
#            out, err, retcode = self.run_shcmd('bjobs %s'%jobid)
#            if retcode==0:
#                for line in out.split('\n'):
#                    items = line.split()
#                    if len(items)>3 and items[0]==jobid:
#                        status = items[2]
#                    elif len(items)>0 and items[-1]=='found':
#                        status = 'FINISHED'
#            else:
#                print('DEBUG: ', out, err, retcode)
#
#            iter += 1
#            if iter>=maxiter:
#                break
#
#        if status=='DONE' or 'FINISHED':
#            self.set_status(result, myname, self.PASSED)
#        else:
#            self.set_status(result, myname, self.FAILED, errmsg='Job completion status is not expected.')
#
#        return result

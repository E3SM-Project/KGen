# kgentest.py

import os
import shutil
import re
import time
from kgutils import run_shcmd
from kext_sys_ch_test import KExtSysCHTest

class KExtSysCHCesmTest(KExtSysCHTest):
    def download(self, myname, result):

        systestdir = result['mkdir_task']['sysdir']
        workdir = result['mkdir_task']['workdir']

        appsrc = '%s/cesm_ref'%systestdir

        if os.path.exists(appsrc):
            # check if cesm exists in appsrc dir
            out, err, retcode = run_shcmd('git status | grep "nothing to commit"', cwd=appsrc)
            if retcode != 0 or not out or not out.startswith('nothing to commit'):
                run_shcmd('rm -rf ' + appsrc, cwd=systestdir)
                run_shcmd('git clone https://github.com/escomp/cesm.git cesm_ref', cwd=systestdir)
                run_shcmd('git checkout cesm2_1_alpha01d', cwd=appsrc)
                run_shcmd('./manage_externals/checkout_externals', cwd=appsrc)
        else:
            run_shcmd('git clone https://github.com/escomp/cesm.git cesm_ref', cwd=systestdir)
            run_shcmd('git checkout cesm2_1_alpha01d', cwd=appsrc)
            run_shcmd('./manage_externals/checkout_externals', cwd=appsrc)

        # copy cesm src into test specific src dir
        tmpsrc = '%s/cesm_work'%systestdir
        if not os.path.exists(tmpsrc):
            shutil.copytree(appsrc, tmpsrc)

        result[myname]['appsrc'] = appsrc
        result[myname]['tmpsrc'] = tmpsrc

        self.set_status(result, myname, self.PASSED)

        return result

#    def build(self, myname, result):
#
#        casedir = result['config_task']['casedir']
#        casename = result['config_task']['casename']
#        statefiles = result['generate_task']['statefiles']
#        workdir = result['mkdir_task']['workdir']
#
#        datadir = '%s/data'%workdir
#        result[myname]['datadir'] = datadir
#
#        if self.REBUILD or not os.path.exists(datadir) or any(not os.path.exists('%s/%s'%(datadir, sf)) for sf in statefiles):
#            if self.LEAVE_TEMP:
#                with open('%s/build_cmds.sh'%casedir, 'w') as f:
#                    f.write('#!/bin/bash\n')
#                    f.write('\n')
#                    f.write('    ./%s.clean_build\n'%casename)
#                    f.write('    ./%s.build'%casename)
#                os.chmod('%s/build_cmds.sh'%casedir, 0755)
#
#            # clean build
#            out, err, retcode = self.run_shcmd('./%s.clean_build'%casename, cwd=casedir)
#            if retcode != 0:
#                self.set_status(result, myname, self.FAILED, errmsg='%s.clean_build is failed.'%casename)
#            else:
#                # build
#                out, err, retcode = self.run_shcmd('./%s.build'%casename, cwd=casedir)
#                if retcode != 0:
#                    self.set_status(result, myname, self.FAILED, errmsg='%s.build is failed.'%casename)
#                else:
#                    self.set_status(result, myname, self.PASSED)
#        else:
#            # copy files from data to kernel directory
#            for statefile in statefiles:
#                shutil.copyfile(os.path.join(datadir, statefile), '%s/kernel/%s'%(workdir, statefile))
#
#            shutil.copyfile(os.path.join(datadir, 'kgen_statefile.lst'), '%s/kernel/kgen_statefile.lst'%workdir)
#
#            result['goto'] = 'runkernel_task'
#            self.set_status(result, myname, self.PASSED)
#
#        return result
#
#    def genstate(self, myname, result):
#
#        casedir = result['config_task']['casedir']
#        casename = result['config_task']['casename']
#        workdir = result['mkdir_task']['workdir']
#
#        # may need to add -P BSUB directive in .run and .st_archive scripts
#
#        # run cesm
#        out, err, retcode = self.run_shcmd('./%s.submit'%casename, cwd=casedir)
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
#                if any(item==casename for item in items):
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

# kgentest.py

import os
import shutil
import getpass
from kext_sys_test import KExtSysTest
from kgutils import run_shcmd

class KExtSysYSTest(KExtSysTest):

    def preprocess(self, myname, result):
        out, err, retcode = run_shcmd('bqueues')

        if retcode != 0 or out.find('caldera')<0 or out.find('geyser')<0 or out.find('regular')<0 or out.find('premium')<0:
            errmsg = 'Current system is not Yellowstone of NCAR'
            self.set_status(result, myname, self.FAILED, errmsg)
        else:
            self.set_status(result, myname, self.PASSED)

        return result

    def mkworkdir(self, myname, result):
        if self.WORK_DIR is None:
            self.WORK_DIR = '/glade/scratch/%s'%getpass.getuser()

        systestdir = '%s/kgensystest'%self.WORK_DIR
        if not os.path.exists(systestdir):
            os.mkdir(systestdir)

        workdir = '%s/%s'%(systestdir, self.TEST_ID.replace('/', '_'))
        if not os.path.exists(workdir):
            os.mkdir(workdir)

        if os.path.exists('%s/kernel'%workdir):
            shutil.rmtree('%s/kernel'%workdir)

        if os.path.exists('%s/state'%workdir):
            shutil.rmtree('%s/state'%workdir)

        result[myname]['sysdir'] = systestdir
        result[myname]['workdir'] = workdir

        self.set_status(result, myname, self.PASSED)

        return result

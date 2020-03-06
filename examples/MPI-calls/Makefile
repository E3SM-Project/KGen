KGEN_HOME := ../..
KGEN := ${KGEN_HOME}/bin/kgen

#PAPI_DIR := /path/to/PAPI

SRC_DIR := ${PWD}/src
SRC := ${SRC_DIR}/update_mod.F90
MPI_INCLUDE := /opt/cray/pe/cray-mvapich2/2.3.1/infiniband/cray/9.0/include

test:
	${KGEN} \
		--mpi header=${MPI_INCLUDE}/mpif.h \
		--cmd-clean "cd ${SRC_DIR}; make -f Makefile.srun clean" \
		--cmd-build "cd ${SRC_DIR}; make -f Makefile.srun build" \
        --cmd-run "cd ${SRC_DIR}; make -f Makefile.srun run" \
		${SRC}

# additional flags
#        --repr-code enable \
#        --repr-etime nbins=5,ndata=20 \
#        --repr-papi header=${PAPI_DIR}/include/f90papi.h,static=${PAPI_DIR}/lib/libpapi.a,event=PAPI_TOT_INS \
#        --source alias=/path/a:path/b # add this option if your system requires alias paths
#        --rebuild all \

clean:
	${MAKE} -f Makefile.srun clean -C src
	rm -rf kernel state kgen.log _kgen_compflag_cmdwrapper.sh strace.log include.ini model model.ini elapsedtime coverage papi

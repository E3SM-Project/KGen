# kgen_extra.py

kgen_file_header = \
"""
! KGEN-generated Fortran source file
!
! Filename    : %s
! Generated at: %s
! KGEN version: %s

"""

kgen_subprograms = \
"""FUNCTION kgen_get_newunit() RESULT(new_unit)
   INTEGER, PARAMETER :: UNIT_MIN=100, UNIT_MAX=1000000
   LOGICAL :: is_opened
   INTEGER :: nunit, new_unit, counter

   new_unit = -1
   DO counter=UNIT_MIN, UNIT_MAX
       inquire(UNIT=counter, OPENED=is_opened)
       IF (.NOT. is_opened) THEN
           new_unit = counter
           EXIT
       END IF
   END DO
END FUNCTION

SUBROUTINE kgen_error_stop( msg )
    IMPLICIT NONE
    CHARACTER(LEN=*), INTENT(IN) :: msg

    WRITE (*,*) msg
    STOP 1
END SUBROUTINE """

kgen_print_counter = \
"""SUBROUTINE kgen_print_counter(counter)
    INTEGER, INTENT(IN) :: counter
    PRINT *, "KGEN writes input state variables at count = ", counter
END SUBROUTINE

SUBROUTINE kgen_print_mpirank_counter(rank, counter)
    INTEGER, INTENT(IN) :: rank, counter
    PRINT *, "KGEN writes input state variables at count = ", counter, " on mpirank = ", rank
END SUBROUTINE"""


kgen_verify_intrinsic_checkpart = \
"""check_status%%numTotal = check_status%%numTotal + 1
IF ( var %s ref_var ) THEN
    check_status%%numIdentical = check_status%%numIdentical + 1
    if(check_status%%VerboseLevel == 3) then
        WRITE(*,*)
        WRITE(*,*) trim(adjustl(varname)), " is IDENTICAL( ", var, " )."
    endif
ELSE
    if(check_status%%VerboseLevel > 0) then
        WRITE(*,*)
        WRITE(*,*) trim(adjustl(varname)), " is NOT IDENTICAL."
        if(check_status%%VerboseLevel == 3) then
            WRITE(*,*) "KERNEL: ", var
            WRITE(*,*) "REF.  : ", ref_var
        end if
    end if
    check_status%%numFatal = check_status%%numFatal + 1
END IF"""

kgen_verify_numeric_array = \
"""check_status%%numTotal = check_status%%numTotal + 1
IF ( ALL( var %(eqtest)s ref_var ) ) THEN

    check_status%%numIdentical = check_status%%numIdentical + 1            
    if(check_status%%VerboseLevel == 3) then
        WRITE(*,*)
        WRITE(*,*) "All elements of ", trim(adjustl(varname)), " are IDENTICAL."
        !WRITE(*,*) "KERNEL: ", var
        !WRITE(*,*) "REF.  : ", ref_var
        IF ( ALL( var == 0 ) ) THEN
            if(check_status%%VerboseLevel == 3) then
                WRITE(*,*) "All values are zero."
            end if
        END IF
    end if
ELSE
    allocate(temp(%(allocshape)s))
    allocate(temp2(%(allocshape)s))

    n = count(var/=ref_var)
    where(abs(ref_var) > check_status%%minvalue)
        temp  = ((var-ref_var)/ref_var)**2
        temp2 = (var-ref_var)**2
    elsewhere
        temp  = (var-ref_var)**2
        temp2 = temp
    endwhere
    nrmsdiff = sqrt(sum(temp)/real(n))
    rmsdiff = sqrt(sum(temp2)/real(n))

    if(check_status%%VerboseLevel > 0) then
        WRITE(*,*)
        WRITE(*,*) trim(adjustl(varname)), " is NOT IDENTICAL."
        WRITE(*,*) count( var /= ref_var), " of ", size( var ), " elements are different."
        if(check_status%%VerboseLevel >= 2 .AND. check_status%%VerboseLevel < 4) then
            WRITE(*,*) "Average - kernel ", sum(var)/real(size(var))
            WRITE(*,*) "Average - reference ", sum(ref_var)/real(size(ref_var))
        endif
        WRITE(*,*) "RMS of difference is ",rmsdiff
        WRITE(*,*) "Normalized RMS of difference is ",nrmsdiff
    end if

    if (nrmsdiff > check_status%%tolerance) then
        check_status%%numFatal = check_status%%numFatal+1
    else
        check_status%%numWarning = check_status%%numWarning+1
    endif

    deallocate(temp,temp2)
END IF"""

kgen_verify_nonreal_array = \
"""check_status%%numTotal = check_status%%numTotal + 1
IF ( ALL( var %(eqtest)s ref_var ) ) THEN

    check_status%%numIdentical = check_status%%numIdentical + 1            
    if(check_status%%VerboseLevel == 3) then
        WRITE(*,*)
        WRITE(*,*) "All elements of ", trim(adjustl(varname)), " are IDENTICAL."
        !WRITE(*,*) "KERNEL: ", var
        !WRITE(*,*) "REF.  : ", ref_var
        IF ( ALL( var == 0 ) ) THEN
                WRITE(*,*) "All values are zero."
        END IF
    end if
ELSE
    if(check_status%%VerboseLevel > 1) then
        WRITE(*,*)
        WRITE(*,*) trim(adjustl(varname)), " is NOT IDENTICAL."
        WRITE(*,*) count( var /= ref_var), " of ", size( var ), " elements are different."
    end if

    check_status%%numFatal = check_status%%numFatal+1
END IF"""

kgen_utils_file_head = \
"""
INTEGER, PARAMETER :: kgen_dp = selected_real_kind(15, 307)

type check_t
    logical :: Passed
    integer :: numFatal
    integer :: numTotal
    integer :: numIdentical
    integer :: numWarning
    integer :: VerboseLevel
    real(kind=kgen_dp) :: tolerance
    real(kind=kgen_dp) :: minvalue
end type check_t

public kgen_dp, check_t, kgen_init_check, kgen_print_check
"""

kgen_utils_file_checksubr = \
"""
subroutine kgen_init_check(check, tolerance, minvalue)
  type(check_t), intent(inout) :: check
  real(kind=kgen_dp), intent(in), optional :: tolerance
  real(kind=kgen_dp), intent(in), optional :: minvalue

  check%Passed   = .TRUE.
  check%numFatal = 0
  check%numWarning = 0
  check%numTotal = 0
  check%numIdentical = 0
  !check%VerboseLevel = 1
  if(present(tolerance)) then
     check%tolerance = tolerance
  else
      check%tolerance = 1.0D-15
  endif
  if(present(minvalue)) then
     check%minvalue = minvalue
  else
      check%minvalue = 1.0D-15
  endif
end subroutine kgen_init_check

subroutine kgen_print_check(kname, check)
   character(len=*) :: kname
   type(check_t), intent(in) ::  check

   if(check%VerboseLevel == 0) then
	write (*,*)
   else if(check%VerboseLevel == 1) then
	write (*,*)
	!write (*,*) TRIM(kname),':' check%numFatal 'errors detected out of' check%numTotal 'checked'
        write (*,*) TRIM(kname),': Tolerance for normalized RMS: ',check%tolerance
        write (*,*) TRIM(kname),': Number of variables checked: ',check%numTotal
	write (*,*) TRIM(kname),': Number of fatal errors detected: ', check%numFatal
   else if(check%VerboseLevel == 2) then
	write (*,*)
        write (*,*) TRIM(kname),': Tolerance for normalized RMS: ',check%tolerance
        write (*,*) TRIM(kname),': Number of variables checked: ',check%numTotal
        write (*,*) TRIM(kname),': Number of warnings detected: ',check%numWarning
        write (*,*) TRIM(kname),': Number of fatal errors detected: ', check%numFatal
   else if(check%VerboseLevel == 3) then
        write (*,*)
        write (*,*) TRIM(kname),': Tolerance for normalized RMS: ',check%tolerance
        write (*,*) TRIM(kname),': Number of variables checked: ',check%numTotal
        write (*,*) TRIM(kname),': Number of Identical results: ',check%numIdentical
        write (*,*) TRIM(kname),': Number of warnings detected: ',check%numWarning
        write (*,*) TRIM(kname),': Number of fatal errors detected: ', check%numFatal
   else
	write (*,*), 'Illegal Verbose level: ', check%VerboseLevel, 'Verbose Level flag must be between 0 and 3'
	STOP
   end if

   if (check%numFatal> 0) then
        write(*,*) TRIM(kname),': Verification FAILED'
   else
        write(*,*) TRIM(kname),': Verification PASSED'
   endif
end subroutine kgen_print_check
"""

rdtsc = \
"""         .file   "rdtsc.s"
         .text
.globl rdtsc_
         .type   rdtsc_, @function
rdtsc_:
         rdtsc
         movl %eax,%ecx
         movl %edx,%eax
         shlq $32,%rax
         addq %rcx,%rax
         ret
         .size   rdtsc_, .-rdtsc_"""

Intrinsic_Procedures = [ \
# numeric functions \
'abs','aimag','aint','anint','ceiling','cmplx','conjg','dble','dim','dprod','floor','int','max','min','mod','modulo','nint','real','sign', \
# mathematical functions \
'acos','asin','atan','atan2','cos','cosh','exp','log','log10','sin','sinh','sqrt','tan','tanh', \
# character functions \
'achar','adjustl','adjustr','char','iachar','ichar','index','len_trim','lge','lgt','lle','llt','max','min','repeat','scan','trim','verify', \
# kind functions \
'kind','selected_char_kind','selected_int_kind','selected_real_kind', \
# miscellaneous type conversion functions \
'logical', 'transfer', \
# numeric inquiry functions \
'digits','epsilon','huge','maxexponent','minexponent','precision','radix','range','tiny', \
# array inquiry functions \
'lbound','shape','size','ubound', \
# other inquiry functions \
'allocated','associated','bit_size','extends_type_of','len','new_line','present','same_type_as', \
# bit manipulation procedures \
'btest','iand','ibclr','ibits','ibset','ieor','ior','ishft','ishftc','mvbits','not', \
# vector and matrix multiply functions \
'exponent','fraction','nearest','rrspacing','scale','set_exponent','spacing','dot_product','matmul', \
# array reduction functions \
'all' ,'any' ,'count' ,'maxval' ,'minval' ,'product' ,'sum', \
# array construction functions \
'cshift','eoshift','merge','pack','reshape','spread','transpose','unpack', \
# array location functions \
'maxloc','minloc', \
# null function \
'null', \
# allocation transfer procedure \
'move alloc', \
# random number subroutines \
'random_number','random_seed', \
# system environment procedures \
'command_argument_count','cpu_time','date_and_time','get_command','get_command_argument','get_environment_variable','is_iostat_end','is_iostat_eor','system_clock', \
# specific names \
'alog','alog10','amax0','amax1','amin0','amin1','amod','cabs','ccos','cexp','clog','csin','csqrt','dabs','dacos','dasin','datan','dcos','dcosh','ddim','dexp','dint','dlog','dlog10','dmax1','dmin1','dmod','dnint','dsign','dsin','dsinh','dsqrt','dtan','dtanh','float','iabs','idim','idint','idnint','ifix','isign','max0','max1','min0','min1' \
]

Intrinsic_Modules = { \
    'ISO_FORTRAN_ENV': [ 'error_unit', 'file_storage_size', 'input_unit', 'iostat_end', 'iostat_eor', 'numeric_storage_size', 'output_unit', 'character_storage_size' ], \
    'ISO_C_BINDING': [ 'c_associated', 'c_f_pointer', 'c_f_procpointer', 'c_funloc', 'c_loc', 'c_sizeof', 'c_int ', 'c_short', 'c_long', 'c_long_long', 'c_signed_char', 'c_size_t', 'c_int8_t', 'c_int16_t', 'c_int32_t', 'c_int64_t', 'c_int_least8_t', 'c_int_least16_t', 'c_int_least32_t', 'c_int_least64_t', 'c_int_fast8_t', 'c_int_fast16_t', 'c_int_fast32_t', 'c_int_fast64_t', 'c_intmax_t', 'c_intptr_t', 'c_ptrdiff_t', 'c_float', 'c_double', 'c_long_double', 'c_float_complex', 'c_double_complex', 'c_long_double_complex', 'c_bool', 'c_char', 'c_null_char', 'c_alert', 'c_backspace', 'c_form_feed', 'c_new_line', 'c_carriage_return', 'c_horizontal_tab', 'c_vertical_tab', 'c_null_ptr', 'c_ptr ', 'c_null_funptr', 'c_funptr ' ], \
    'IEEE_EXCEPTIONS': [ 'ieee_flag_type', 'ieee_status_type', 'ieee_support_flag', 'ieee_support_halting', 'ieee_get_flag', 'ieee_get_halting_mode', 'ieee_get_status', 'ieee_set_flag', 'ieee_set_halting_mode', 'ieee_set_status' ], \
    'IEEE_ARITHMETIC': [ 'ieee_class_type', 'ieee_round_type', 'ieee_support_datatype', 'ieee_support_divide', 'ieee_support_denormal', 'ieee_support_inf', 'ieee_support_io', 'ieee_support_nan', 'ieee_support_rounding', 'ieee_support_standard', 'ieee_support_underflow_control', 'ieee_support_sqrt', 'ieee_class', 'ieee_copy_sign', 'ieee_is_finite', 'ieee_is_nan', 'ieee_is_normal', 'ieee_is_negative', 'ieee_is_logb', 'ieee_next_after', 'ieee_rem', 'ieee_rint', 'ieee_scalb', 'ieee_unordered', 'ieee_value', 'ieee_selected_real_kind', 'ieee_get_rounding_mode', 'ieee_get_underflow_mode', 'ieee_set_rounding_mode', 'ieee_set_underflow_mode' ], \
    'IEEE_FEATURES': [ 'ieee_features_type' ] \
}


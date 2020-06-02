"""
 OCCAM

 Copyright (c) 2011-2020, SRI International

  All rights reserved.

 Redistribution and use in source and binary forms, with or without
 modification, are permitted provided that the following conditions are met:

 * Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.

 * Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

 * Neither the name of SRI International nor the names of its contributors may
   be used to endorse or promote products derived from this software without
   specific prior written permission.

 THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
 AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
 DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
 FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
 DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
 SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
 CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
 OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
 OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import sys
import os
import tempfile
import shutil

from . import config

from . import driver

from . import interface as inter

from . import stringbuffer

from . import pool

from . import utils  


def interface(input_file, output_file, wrt):
    """ computing the interfaces.
    """
    args = ['-Pinterface', '-Pinterface-output', output_file]
    args += driver.all_args('-Pinterface-entry', wrt)
    return driver.previrt(input_file, '/dev/null', args)

def specialize(input_file, output_file, rewrite_file, interfaces, \
               policy, max_bounded):
    """ inter module specialization.
    """
    args = ['-Pspecialize']
    if not rewrite_file is None:
        args += ['-Pspecialize-output', rewrite_file]
    args += driver.all_args('-Pspecialize-input', interfaces)
    if policy <> 'none':
        args += ['-Pspecialize-policy={0}'.format(policy)]
    if policy == 'bounded':
        args += ['-Pspecialize-max-bounded={0}'.format(max_bounded)]
    if output_file is None:
        output_file = '/dev/null'
    return driver.previrt(input_file, output_file, args)

def rewrite(input_file, output_file, rewrites, output=None):
    """ inter module rewriting
    """
    args = ['-Prewrite'] + driver.all_args('-Prewrite-input', rewrites)
    return driver.previrt_progress(input_file, output_file, args, output)

def force_inline(input_file, output_file, inline_bounce, inline_specialized, output=None):
    """ Force inlining of special functions
    """
    if not inline_bounce and not inline_specialized:
        shutil.copy(input_file, output_file)
        return 0
    
    args = ['-Pinliner']
    if inline_bounce:
        sys.stderr.write("\tinlining bounce functions generated by devirt\n")
        args += ['-Pinline-bounce-functions']
    if inline_specialized:
        sys.stderr.write("\tinlining specialized functions\n")
        args += ['-Pinline-specialized-functions']
    return driver.previrt_progress(input_file, output_file, args, output)

def internalize(input_file, output_file, interfaces, whitelist):
    """ marks unused symbols as internal/hidden
    """
    args = ['-Pinternalize'] + \
           driver.all_args('-Pinternalize-wrt-interfaces', interfaces)
                           
    if whitelist is not None:
        args = args + ['-Pkeep-external', whitelist]
    return driver.previrt_progress(input_file, output_file, args)

def strip(input_file, output_file):
    """ strips unused symbols
    """
    args = [input_file, '-o', output_file]
    args += ['-strip', '-strip-dead-prototypes']             
    return driver.run(config.get_llvm_tool('opt'), args)

def devirt(devirt_method, input_file, output_file):
    """use seadsa to resolve indirect function calls by adding multiple
    direct calls
    """
    assert(devirt_method <> 'none')
    args = [ '-Pdevirt'
            #, '-Presolve-incomplete-calls=true'
            #, '-Pmax-num-targets=15'
    ]

    if devirt_method == 'sea_dsa_with_cha': 
        args += ['-Pdevirt-with-cha']

    if devirt_method == 'sea_dsa': 
        args += ['-sea-dsa-type-aware=true']

    retcode = driver.previrt_progress(input_file, output_file, args)
    if retcode != 0:
        return retcode

    #FIXME: previrt_progress returns 0 in cases where --Pdevirt may crash.
    #Here we check that the output_file exists
    if not os.path.isfile(output_file):
        #Some return code different from zero
        return 3
    else:
        return retcode


def profile(input_file, output_file):
    """ count number of instructions, functions, memory accesses, etc.
    """
    args = ['-Pprofiler']
    args += [
        ## XXX: these can be expensive        
        '-profile-verbose=false'
        ,'-profile-loops=true'
        ,'-profile-safe-pointers=true'
    ]
    args += ['-profile-outfile={0}'.format(output_file)]
    return driver.previrt(input_file, '/dev/null', args)

def clam(cmd, input_file, output_file):
    """ running clam (https://github.com/seahorn/crab-llvm) 
    """
    # analysis options    
    args = [
            #### Abstract domain 
              '--crab-dom=int'
            #### To avoid code bloating 
            , '--crab-lower-select=false'
            , '--crab-lower-unsigned-icmp=false'
            , '--crab-lower-constant-expr=false'
            , '--crab-lower-switch=false'
            , '--crab-lower-invoke=false'
            #### Reason about register and memory contents
            , '--crab-track=arr'
            , '--crab-disable-ptr'
            , '--crab-singleton-aliases'
            #### We use for now context-insensitive
            , '--crab-heap-analysis=ci-sea-dsa'
            #### Options to insert invariants as llvm.assume instructions
            #, '--crab-add-invariants=block-entry', '--crab-promote-assume'        
            #, '--crab-add-invariants=loop-header', '--crab-promote-assume'
            #, '--crab-add-invariants=all', '--crab-promote-assume'
            , '--crab-add-invariants=dead-code'
            #### for debugging
            #, '--crab-print-invariants'
            #, '--crab-verbose=0'
            #, '--crab-stats'
    ]
    args += [input_file, '--o={0}'.format(output_file)]
    sb = stringbuffer.StringBuffer()
    res = driver.run(cmd, args, sb, False)
    ### uncomment for debugging:
    #print str(sb)
    return res

def peval(input_file, output_file, \
          opt_options, \
          policy, max_bounded, \
          devirt_method, \
          force_inline_bounce, force_inline_spec, \
          use_ipdse, use_ai_dce, log=None):
    """ intra module specialization/optimization
    """
    opt = tempfile.NamedTemporaryFile(suffix='.bc', delete=False)
    done = tempfile.NamedTemporaryFile(suffix='.bc', delete=False)
    tmp = tempfile.NamedTemporaryFile(suffix='.bc', delete=False)
    opt.close()
    done.close()
    tmp.close()

    def _optimize(input_file, output_file, use_seaopt):
        retcode = optimize(input_file, output_file, use_seaopt, opt_options)
        if retcode != 0:
            sys.stderr.write("ERROR: intra module optimization failed!\n")
            shutil.copy(input_file, output_file)
        else:
            sys.stderr.write("\tintra module optimization finished succesfully\n")
        return retcode

    ## Only for debugging or tests
    disable_opt = False
    
    if disable_opt:
        shutil.copy(input_file, done.name)
    else:
        # Optimize using standard llvm transformations before any other
        # optional pass. Otherwise, these passes will not be very effective.
        retcode = _optimize(input_file, done.name, use_ai_dce or use_ipdse)
        if retcode != 0: return retcode

    if devirt_method <> 'none':
        if devirt_method == 'sea_dsa' or \
           devirt_method == 'sea_dsa_with_cha':
            # Promote indirect calls to direct calls
            retcode = devirt(devirt_method, done.name, tmp.name)
            if retcode != 0:
                sys.stderr.write("ERROR: resolution of indirect calls failed!\n")
                shutil.copy(done.name, output_file)
                return retcode
            sys.stderr.write("\tresolved indirect calls finished succesfully\n")
            # Force inlining bounce functions (if added)
            force_inline(tmp.name, done.name, force_inline_bounce, False)
                    
    if use_ipdse:
        ## 1. lower global initializers to store's in main 
        passes = ['-lower-gv-init']
        ## 2. dead store elimination based on sea-dsa (improve
        ##    precision of sccp)
        passes += [
                   ###Context-insensitive sea-dsa  
                   '-sea-dsa=ci', '-horn-sea-dsa-local-mod',
                   ##Inter-procedural dead store elimination
                   '-ip-dse', '-ip-dse-max-def-use=25']
        ## 3. perform IPSCCP
        passes += ['-Pipsccp']
        ## 4. cleanup after IPSCCP
        passes += ['-dce', '-globaldce']
        retcode = driver.previrt(done.name, tmp.name, passes)
        if retcode != 0:
            sys.stderr.write("ERROR: ipdse failed!\n")
            shutil.copy(done.name, output_file)
            #FIXME: unlink files
            return retcode
        else:
            sys.stderr.write("\tipdse finished succesfully\n")
        shutil.copy(tmp.name, done.name)

    if use_ai_dce:
        clam_cmd = utils.get_clam()
        if clam_cmd is None:
            sys.stderr.write('crab not found: skipping ai-based dce')
        else:
            utils.write_timestamp("Starting crab found here " + utils.get_clam())
            retcode = clam(clam_cmd, done.name, tmp.name)
            if retcode != 0:
                sys.stderr.write("ERROR: crab failed!\n")
                shutil.copy(done.name, output_file)
                return retcode
            else:
                utils.write_timestamp("Finished crab")
                ## XXX: commented the code because we don't add llvm.assume right now.
                ## After crab-llvm insert llvm.assume instructions we must run
                ## the optimizer again.
                # shutil.copy(tmp.name, done.name)
                # retcode = _optimize(tmp.name, done.name, use_ai_dce)
                # if retcode != 0:
                #     return retcode
            shutil.copy(tmp.name, done.name)
            
    if policy <> 'none':
        out = ['']
        iteration = 0
        while True:
            iteration += 1
            if iteration > 1 or \
               use_ipdse:
                # optimize using standard llvm transformations
                retcode = _optimize(done.name, opt.name, use_ai_dce or use_ipdse)
                if retcode != 0:
                    break;
            else:
                shutil.copy(done.name, opt.name)

            # perform specialization using policies
            pass_args = ['-Ppeval', '-Ppeval-policy={0}'.format(policy), '-Ppeval-opt']
            if policy == 'bounded':
                pass_args += ['-Ppeval-max-bounded={0}'.format(max_bounded)]
                
            progress = driver.previrt_progress(opt.name, tmp.name, pass_args, output=out)
            sys.stderr.write("\tintra-module specialization finished\n")
            # forcing inlining of specialized functions if option is enabled
            force_inline(tmp.name, done.name, False, force_inline_spec)
            
            if progress:
                if log is not None:
                    log.write(out[0])
            else:
                break
    else:
        print "\tskipped intra-module specialization"

    shutil.copy(done.name, output_file)
    try:
        os.unlink(done.name)
        os.unlink(opt.name)
        os.unlink(tmp.name)
    except OSError:
        pass
    return retcode

def optimize(input_file, output_file, use_seaopt, extra_opts):
    """ Run opt -O3.
        The optimizer is tuned for code debloating and not necessarily
        for runtime performance.
    """
    args = ['-disable-simplify-libcalls']
    ## We disable loop vectorization because some of our analysis
    ## cannot support them.
    ## LLVM 10: --disable-loop-vectorization is gone
    args += ['--disable-slp-vectorization']
             
    use_seaopt = use_seaopt and utils.found_seaopt()
    if use_seaopt:
        # disable sinking instructions to end of basic block
        # this might create unwanted aliasing scenarios (in sea-dsa)
        # for now, there is no option to undo this switch        
        args += ['--simplifycfg-sink-common=false']
        # disable loop rotation because it's pretty bad for crab
        ## LLVM 10: --disable-loop-rotate is gone.
        #args += ['--disable-loop-rotate']
        
    args += extra_opts
    args += [input_file, '-o', output_file, '-O3']
    return driver.run(utils.get_opt(use_seaopt), args)

def partial_specialize_program_args(input_file, output_file, cnstrs, filename=None):
    """ constrain the program arguments.
    """
    if filename is None:
        cnstr_file = tempfile.NamedTemporaryFile(delete=False)
        cnstr_file.close()
        cnstr_file = cnstr_file.name
    else:
        cnstr_file = filename
    f = open(cnstr_file, 'w')
    (argc, argv) = cnstrs
    f.write('{0}\n'.format(argc))
    index = 0
    for x in argv:
        f.write('{0} {1}\n'.format(index, x))
        index += 1
    f.close()

    args = ['-Ppartial-cmdline-spec', '-Ppartial-cmdline-spec-input', cnstr_file]
    driver.previrt(input_file, output_file, args)

    if filename is None:
        os.unlink(cnstr_file)

def full_specialize_program_args(input_file, output_file, args, filename=None, name=None):
    """ fix the program arguments.
    """
    if filename is None:
        arg_file = tempfile.NamedTemporaryFile(delete=False)
        arg_file.close()
        arg_file = arg_file.name
    else:
        arg_file = filename
    f = open(arg_file, 'w')
    for x in args:
        f.write(x + '\n')
    f.close()

    extra_args = []
    if not name is None:
        extra_args = ['-Pfull-cmdline-spec-name', name]
    args = ['-Pfull-cmdline-spec', '-Pfull-cmdline-spec-input', arg_file] + extra_args
    driver.previrt(input_file, output_file, args)

    if filename is None:
        os.unlink(arg_file)

def config_prime(input_file, output_file, known_args, num_unknown_args):
    """ 
    Execute the program until a branch condition is unknown.
    known_args is a list of strings
    num_unknown_args is a non-negative number.
    """
    ## TODOX: find subset of -O1 that simplify loops for dominance queries
    args = ['-O1'] # '-loop-simplify', '-simplifycfg'
    args += ['-Pconfig-prime']
    index = 0
    for x in known_args:
        if index == 0:
            args.append('-Pconfig-prime-file=\"{0}\"'.format(x))
        else:
            args.append('-Pconfig-prime-input-arg=\"{0}\"'.format(x))
        index += 1
    args.append('-Pconfig-prime-unknown-args={0}'.format(num_unknown_args))
    driver.previrt(input_file, output_file, args)
    
def deep(libs, ifaces):
    """ compute interfaces across modules.
    """
    tf = tempfile.NamedTemporaryFile(suffix='.iface', delete=False)
    tf.close()
    iface = inter.parseInterface(ifaces[0])
    for i in ifaces[1:]:
        inter.joinInterfaces(iface, inter.parseInterface(i))

    inter.writeInterface(iface, tf.name)

    progress = True
    while progress:
        progress = False
        for l in libs:
            interface(l, tf.name, [tf.name])
            x = inter.parseInterface(tf.name)
            progress = inter.joinInterfaces(iface, x) or progress
            inter.writeInterface(iface, tf.name)

    os.unlink(tf.name)
    return iface



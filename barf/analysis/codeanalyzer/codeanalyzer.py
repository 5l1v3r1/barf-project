# Copyright (c) 2014, Fundacion Dr. Manuel Sadosky
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:

# 1. Redistributions of source code must retain the above copyright notice, this
# list of conditions and the following disclaimer.

# 2. Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import logging

import barf.core.smt.smtfunction as smtfunction
import barf.core.smt.smtsymbol as smtsymbol

from barf.core.reil import ReilImmediateOperand
from barf.core.reil import ReilMnemonic
from barf.core.reil import ReilRegisterOperand

logger = logging.getLogger(__name__)


class GenericRegister(object):

    """Generic register representation for code analyzer.
    """

    def __init__(self, name, size=None, value=None):

        # Name, size and value of the register
        self._name = name
        self._size = size
        self._value = value

    @property
    def name(self):
        """Get register name.
        """
        return self._name

    @name.setter
    def name(self, value):
        """Set register name.
        """
        self._name = value

    @property
    def size(self):
        """Get register size.
        """
        return self._size

    @size.setter
    def size(self, value):
        """Get register size.
        """
        self._size = value

    @property
    def value(self):
        """Get register value.
        """
        return self._value

    @value.setter
    def value(self, value):
        """Set register value.
        """
        self._value = value

    def __str__(self):
        return "%s : 0x%08x" % (self._name, self._value)


class GenericFlag(object):

    """Generic flag representation for code analyzer.
    """

    def __init__(self, name, value=None):

        # Name and value of the flag
        self._name = name
        self._value = value

    @property
    def name(self):
        """Get flag name.
        """
        return self._name

    @name.setter
    def name(self, value):
        """Set flag name.
        """
        self._name = value

    @property
    def value(self):
        """Get flag value.
        """
        return self._value

    @value.setter
    def value(self, value):
        """Set flag name.
        """
        self._value = value

    def __str__(self):
        return "%s : 0x%08x" % (self._name, self._value)


class GenericContext(object):

    """Generic context for code analyzer.
    """

    def __init__(self, registers, flags, memory):

        # Set of registers.
        self._registers = registers

        # Set of flags.
        self._flags = flags

        # A dictionary-based representation of memory.
        self._memory = memory

    @property
    def registers(self):
        """Get context's registers.
        """
        return self._registers

    @registers.setter
    def registers(self, value):
        """Set context's registers.
        """
        self._registers = value

    @property
    def flags(self):
        """Get context's flags.
        """
        return self._flags

    @flags.setter
    def flags(self, value):
        """Set context's flags.
        """
        self._flags = value

    @property
    def memory(self):
        """Get context's memory.
        """
        return self._memory

    @memory.setter
    def memory(self, value):
        """Set context's memory.
        """
        self._memory = value

    def __str__(self):
        string = "[+] Context :\n"

        string += "    * Registers :\n"
        for _, gen_reg in self._registers.items():
            string += "        " + str(gen_reg) + "\n"

        string += "    * Flags :\n"
        for _, gen_flag in self._flags.items():
            string += "        " + str(gen_flag) + "\n"

        string += "    * Memory :\n"
        for addr, value in self._memory.items():
            string += "        0x%08x : 0x%08x" % (addr, value) + "\n"

        return string


class CodeAnalyzer(object):

    """Implements code analyzer using a SMT solver.
    """

    def __init__(self, solver, translator, arch):

        # A SMT solver instance
        self._solver = solver

        # A SMT translator instance
        self._translator = translator

        # A context (registers and memory)
        self._context = None

        # Architecture information of the binary.
        self._arch_info = arch

    def set_context(self, context):
        """Set context for the SMT solver.
        """
        self._context = context

        # Add each register and its value to the context of the SMT
        # solver as an assertion.
        for _, gen_reg in self._context.registers.items():
            smt_reg = self._translator.make_bitvec(gen_reg.size, self._translator.get_init_name(gen_reg.name))
            self._solver.add(smt_reg == gen_reg.value)

        # Add each flag and its value to the context of the SMT solver
        # as an assertion.
        # TODO: Flag size should be 1 bit.
        for _, gen_flag in self._context.flags.items():
            smt_flag = self._translator.make_bitvec(32, self._translator.get_init_name(gen_flag.name))

            self._solver.add(smt_flag == gen_flag.value)

        # Add each memory location and its content to the SMT solver
        # as an assertion.
        mem = self._translator.get_memory()

        for addr, value in self._context.memory.items():
            self._solver.add(mem[addr] == value)

    def get_context(self):
        """Get context from the SMT solver.
        """
        # Get final values from the SMT solver for the registers set in
        # the initial context.
        registers = {}

        for reg_name, gen_reg in self._context.registers.items():
            symbol = self._solver.declarations[self._translator.get_curr_name(reg_name)]
            value = self._solver.get_value(symbol)
            registers[reg_name] = GenericRegister(reg_name, gen_reg.size, value)

        # Get final values from the SMT solver for the flags set in the
        # initial context.
        # TODO: Flag size should be 1 bit.
        flags = {}

        for flag_name, _ in self._context.flags.items():
            symbol = self._solver.declarations[self._translator.get_curr_name(flag_name)]
            value = self._solver.get_value(symbol)
            flags[flag_name] = GenericFlag(flag_name, value)

        # Get final values from the SMT solver for the memory locations
        # set in the initial context.
        memory = {}

        mem = self._translator.get_memory()

        for addr, _ in self._context.memory.items():
            value = self._solver.get_value(mem[addr])
            memory[addr] = value

        return GenericContext(registers, flags, memory)

    def check_path_satisfiability(self, path, start_address):
        """Check satisfiability of a basic block path.
        """
        start_instr_found = False
        sat = False

        # Traverse basic blocks, translate its instructions to SMT
        # expressions and add them as assertions.
        for bb_curr, bb_next in zip(path[:-1], path[1:]):
            logger.info("BB @ {:#x}".format(bb_curr.address))

            # For each dual instruction...
            for dinstr in bb_curr:
                # If the start instruction have not been found, keep
                # looking...
                if not start_instr_found:
                    if dinstr.address == start_address:
                        start_instr_found = True
                    else:
                        continue

                logger.info("{:#x} {}".format(dinstr.address, dinstr.asm_instr))

                # For each REIL instruction...
                for reil_instr in dinstr.ir_instrs:
                    logger.info("{:#x} {:02d} {}".format(reil_instr.address >> 0x8, reil_instr.address & 0xff, reil_instr))

                    if reil_instr.mnemonic == ReilMnemonic.JCC:
                        # Check that the JCC is the last instruction of
                        # the basic block (skip CALL instructions.)
                        if dinstr.address + dinstr.asm_instr.size - 1 != bb_curr.end_address:
                            logger.error("Unexpected JCC instruction: {:#x} {} ({})".format(dinstr.address, dinstr.asm_instr, reil_instr))

                            # raise Exception()

                            continue

                        # Make sure branch target address from current
                        # basic block is the start address of the next.
                        assert(bb_curr.taken_branch == bb_next.address or
                               bb_curr.not_taken_branch == bb_next.address or
                               bb_curr.direct_branch == bb_next.address)

                        # Set branch condition accordingly.
                        if bb_curr.taken_branch == bb_next.address:
                            branch_var_goal = 0x1
                        elif bb_curr.not_taken_branch == bb_next.address:
                            branch_var_goal = 0x0
                        else:
                            continue

                        # Add branch condition goal constraint.
                        branch_var = self.get_operand_var(reil_instr.operands[0])

                        self.add_constraint(branch_var == branch_var_goal)

                        # The JCC instruction was the last within the
                        # current basic block. End this iteration and
                        # start next one.
                        break

                    # Translate and add SMT expressions to the solver.
                    for smt_expr in self._translator.translate(reil_instr):
                        logger.info("{}".format(smt_expr))

                        self._solver.add(smt_expr)

            sat = self._solver.check() == 'sat'

            logger.info("BB @ {:#x} sat? {}".format(bb_curr.address, sat))

            if not sat:
                break

        # Return satisfiability.
        return sat

    def reset(self, full=False):
        """Reset current state of the analyzer.
        """
        self._solver.reset()

        if full:
            self._translator.reset()

    def get_operand_var(self, operand):
        return self._translator._translate_src_oprnd(operand)

    def get_operand_expr(self, operand, mode="post"):
        if isinstance(operand, ReilRegisterOperand):
            if operand.name in self._arch_info.registers_all:
                # Process architectural registers (eax, ebx, etc.)
                expr = self.get_register_expr(operand.name, mode=mode)
            else:
                # Process temporal registers (t0, t1, etc.)
                var_name = self._get_var_name(operand.name, mode)
                expr = self._translator.make_bitvec(operand.size, var_name)
        elif isinstance(operand, ReilImmediateOperand):
            expr = self.get_immediate_expr(operand.immediate, operand.size)
        else:
            raise Exception("Invalid operand: %s" % str(operand))

        return expr

    def get_immediate_expr(self, immediate, size):
        """Return a smt bit vector that represents an immediate value.
        """
        return smtsymbol.Constant(size, immediate)

    def get_register_expr(self, register_name, mode="post"):
        """Return a smt bit vector that represents a register.
        """
        reg_info = self._arch_info.alias_mapper.get(register_name, None)

        if reg_info:
            var_base_name, offset = reg_info

            var_name = self._get_var_name(var_base_name, mode)
            var_size = self._arch_info.registers_size[var_base_name]

            ret_val = self._translator.make_bitvec(var_size, var_name)
            ret_val = smtfunction.extract(
                ret_val,
                offset,
                self._arch_info.registers_size[register_name]
            )
        else:
            var_name = self._get_var_name(register_name, mode)
            var_size = self._arch_info.registers_size[register_name]

            ret_val = self._translator.make_bitvec(var_size, var_name)

        return ret_val

    def get_memory_expr(self, address, size, mode="post"):
        """Return a smt bit vector that represents a memory location.
        """
        mem = self.get_memory(mode)

        bytes_exprs = []

        for index in xrange(0, size):
            bytes_exprs.append(mem[address + index])

        return smtfunction.concat(8, *reversed(bytes_exprs))

    def get_memory(self, mode):
        """Return a smt bit vector that represents a memory location.
        """
        if mode == "pre":
            mem = self._translator.get_memory_init()
        elif mode == "post":
            mem = self._translator.get_memory()
        else:
            raise Exception()

        return mem

    def add_instruction(self, reil_instruction):
        """Add an instruction for analysis.
        """
        smt_exprs = self._translator.translate(reil_instruction)

        for smt_expr in smt_exprs:
            self._solver.add(smt_expr)

    def add_constraint(self, constraint):
        """Add constraint to the current set of formulas.
        """
        self._solver.add(constraint)

    def set_preconditions(self, conditions):
        """Add preconditions to the analyzer.
        """
        for cond in conditions:
            self._solver.add(cond)

    def set_postconditions(self, conditions):
        """Add postconditions to the analyzer.
        """
        for cond in conditions:
            self._solver.add(cond)

    def check(self):
        """Check if the instructions and restrictions added so far are
        satisfiable.

        """
        return self._solver.check()

    def get_expr_value(self, expr):
        """Get a value for an expression.
        """
        return self._solver.get_value(expr)

    # Auxiliary methods
    # ======================================================================== #
    def _get_var_name(self, register_name, mode):
        """Get variable name for a register considering pre and post mode.
        """
        if mode == "pre":
            var_name = self._translator.get_init_name(register_name)
        elif mode == "post":
            var_name = self._translator.get_curr_name(register_name)
        else:
            raise Exception()

        return var_name

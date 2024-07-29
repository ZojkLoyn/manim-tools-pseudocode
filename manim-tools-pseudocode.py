'''A simple tool to pack the pseudocode of a function

It's used to pack the pseudocode of a function and encode it into a string, so that the pseudocode can be stored in the code and the source code will not be lose after pre-compiled and moved.

  Typical usage example:
'''

__all__ = ["pseudocode", "pseudocode_pack_base"]

import zlib
import json
import re
import inspect
from types import *
from warnings import warn
from functools import wraps


def subdict(obj: object, keys: list[str]) -> dict[str, object]:
    '''return the sub dict of attributes of obj with keys

    parameters:
    obj: object, the object to get sub dict
    keys: list[str], the keys of attributes to get

    return:
    dict[str, object], the sub dict of attributes of obj with keys
    '''
    return {key: getattr(obj, key) for key in keys if hasattr(obj, key)}


PSEUDOCODE_DEFAULT_ENCODING = "utf-8"


class pseudocode_pack_base:
    '''base class for pseudocode pack'''

    class pseudocode_rule:
        '''rule for pseudocode
        
          def pseudocode_name(start_marker):
              code for start_marker
              ### next_marker
              code for next_marker
        '''

        ## prefix_str, is_code_pre-compiled, ..., clip_slice, pattern
        pattern = {
            "start_marker":
            ("\s*def\s*{func_name}%s", False, slice(1, -2), "\(.*\):"),
            "marker": ("\s*%s", True, slice(3, None), "###\s*.*\s*"),
        }
        pattern_code = {
            key + "_code": value[0] % value[-1]
            for key, value in pattern.items()
        }
        pattern_pattern = {
            key + "_pattern": value[-1]
            for key, value in pattern.items()
        }
        pattern_slice = {
            key + "_slice": value[-2]
            for key, value in pattern.items()
        }
        pattern_code_compiled = {
            key + "_code_compiled": re.compile(value[0] % value[-1])
            for key, value in pattern.items() if value[1]
        }
        pattern_pattern_compiled = {
            key + "_pattern_compiled": re.compile(value[-1])
            for key, value in pattern.items()
        }
        rule = dict(**pattern_code, **pattern_code_compiled, **pattern_pattern,
                    **pattern_slice, **pattern_pattern_compiled)

        def clip_pattern(self, attr: str, line: str) -> str:
            return getattr(self, attr +
                           "_pattern_compiled").search(line).group()[getattr(
                               self, attr + "_slice")].strip()

        def __init__(self):
            '''init the rule'''
            self.__dict__.update(self.__class__.rule)

        def deal_with(self, pseudocode_sourcelines: list[str],
                      func: FunctionType) -> list[str]:
            '''deal with the pseudocode source lines

            parameters:
            pseudocode_sourcelines: list[str], the source lines of pseudocode
            func: FunctionType, the function of the pseudocode

            return:
            list[str], the source lines of pseudocode after dealing with the rule
            '''

            pseudocode_sourcelines = [
                line.rstrip() for line in pseudocode_sourcelines
                if not line.isspace()
            ]
            ## get the head line of function def
            start_marker_code_compiled = re.compile(
                self.start_marker_code.format(func_name=func.__name__))
            head = 0
            while start_marker_code_compiled.fullmatch(
                    pseudocode_sourcelines[head]) is None:
                head += 1

            ## get start_marker
            def_str = pseudocode_sourcelines[head]
            start_marker = self.clip_pattern("start_marker", def_str)

            ## get the source pack
            pack = [[start_marker, []]]
            indents = []

            for line in pseudocode_sourcelines[head + 1:]:
                if self.marker_code_compiled.fullmatch(line) is not None:
                    ## pack
                    marker = self.clip_pattern("marker", line)
                    pack.append([marker, []])
                else:
                    pack[-1][-1].append(line)

                    line_indent = line.find(line.lstrip())
                    indents.append(line_indent)

            ## remove indent
            least_indent = min(indents)
            for block in pack:
                block[-1] = [line[least_indent:] for line in block[-1]]

            return pack

    @classmethod
    def generate_pack_encoded(
            cls,
            pseudocode_sourcelines: list[str],
            func: FunctionType,
            encoding: str = PSEUDOCODE_DEFAULT_ENCODING) -> str:
        '''generate the pack encoded from the pseudocode source lines

        parameters:
        pseudocode_sourcelines: list[str], the source lines of pseudocode
        func: FunctionType, the function of the pseudocode
        encoding: str, the encoding of the pack

        return:
        str, the pack encoded
        '''
        pseudocode_sourcepack = cls.pseudocode_rule().deal_with(
            pseudocode_sourcelines, func)

        source_bytes = json.dumps(pseudocode_sourcepack,
                                  separators=(',', ':')).encode(encoding)
        source_compressed_bytes = zlib.compress(source_bytes)
        return source_compressed_bytes.hex()

    @classmethod
    def pack_decode_from(cls,
                         pseudocode_pack_encoded: str,
                         encoding: str = PSEUDOCODE_DEFAULT_ENCODING) -> list:
        '''decode the pack from the pack encoded

        parameters:
        pseudocode_pack_encoded: str, the pack encoded
        encoding: str, the encoding of the pack

        return:
        list, the source pack of the pack
        '''
        source_bytes = zlib.decompress(bytes.fromhex(pseudocode_pack_encoded))
        sourcepack = json.loads(source_bytes.decode(encoding))
        return sourcepack

    WRAPPER_ASSIGNMENTS = ('__module__', '__name__', '__qualname__', '__doc__')

    def __init__(self,
                 origin_pseudocode_pack_encoded: str,
                 warning_update: bool = False,
                 func: FunctionType | None = None,
                 encoding: str = PSEUDOCODE_DEFAULT_ENCODING):
        '''init the pack

        parameters:
        origin_pseudocode_pack_encoded: str, the pack encoded
        warning_update: bool, whether to warn the update
        encoding: str, the encoding of the pack
        '''
        self._origin_pack_encoded = origin_pseudocode_pack_encoded
        self._warning_update = warning_update
        self.encoding = encoding

        self._source_pack = self.__class__.pack_decode_from(
            origin_pseudocode_pack_encoded, encoding=encoding)
        self._dict_index = {
            block[0]:block[1] for block in self._source_pack
        }

        ## update wrapper
        if func is not None:
            for attr in self.__class__.WRAPPER_ASSIGNMENTS:
                setattr(self, attr, getattr(func, attr))

        self._try_warning()
    
    def __getitem__(self,index:str):
        return self._dict_index[index]
    
    def __call__(self,return_line:bool = False):
        if return_line:
            for block in self._source_pack:
                for line in block[1]:
                    yield line
        else:
            for block in self._source_pack:
                yield block

    def _try_warning(self):
        '''try to warn the update and return self'''
        if self._warning_update:
            if not hasattr(self, "_warning_update_info"):
                _warning_update_info = '"{func_name}" need to be updated with: \n{head}"{origin_pack_encoded}"{tail}'.format(
                    func_name=self.__qualname__,
                    head="=" * 8 + "\n",
                    tail="\n" + "=" * 8,
                    origin_pack_encoded=self._origin_pack_encoded)
                self._warning_update_info = _warning_update_info
            warn(self._warning_update_info)
        return self

    @property
    def origin_pack_encoded(self):
        '''return the origin pack encoded'''
        return self.origin_pack_encoded

    @property
    def origin_pack_sourcepack(self):
        '''return the origin pack sourcelines'''
        return self._source_pack


class pseudocode:

    def __init__(self,
                 dumped_pseudocode_pack_encoded: str = None,
                 pack_base: type[pseudocode_pack_base] = pseudocode_pack_base,
                 encoding=PSEUDOCODE_DEFAULT_ENCODING):
        '''init the decorator

        parameters:
        dumped_pseudocode_pack_encoded: str, the pack encoded of the pseudocode, or default None as need to be updated
        pack_base: type[pseudocode_pack_base], the base class of the pack
        encoding: str, the encoding of the pack
        '''
        self.dumped_pseudocode_pack_encoded = dumped_pseudocode_pack_encoded
        self.pack_base = pack_base
        self.encoding = encoding

    def __call__(self, func: FunctionType):
        '''call the decorator

        parameters:
        func: FunctionType, the function to be changed into pseudocode

        return:
        `pseudocode_pack_base`, the pack of the pseudocode
        '''

        dumped_pack_encoded = self.dumped_pseudocode_pack_encoded

        ## get source pack list
        try:
            source_lines = inspect.getsourcelines(func)[0]
            has_source_lines = True
        except OSError:
            has_source_lines = False

        ## build the pack
        if has_source_lines:
            ## match source and dumped
            source_pack_encoded = self.pack_base.generate_pack_encoded(
                source_lines, func=func, encoding=self.encoding)
            if source_pack_encoded != dumped_pack_encoded:
                warning_update = True
            else:
                warning_update = False
            pack = self.pack_base(source_pack_encoded, warning_update, func)

        else:
            pack = self.pack_base(dumped_pack_encoded, False, func)

        return pack


if __name__ == "__main__":

    class bibi:

        @pseudocode(
            "789c8b8e562a4f2c57d289568a51ca4bcccd8c5152d2512a482c2e568a8d8d050084cb08f4"
        )
        def hoho(waw):
            "nami"
            pass

    @pseudocode(
        "789c8b8e562acf2f57d289562a29aab4528a8d05b212f3f24b32528be273138bb2538b40720a40909d9f9aafa4a3945a919c5a50620564810413a313ad12538a63811a63018ae01732"
    )
    def hihi(wow):
        try:
            ### another_marker
            koeo
        except:
            a[a:ads]

    print([line for line in hihi(return_line=True)])
    print(bibi.hoho.origin_pack_sourcepack)

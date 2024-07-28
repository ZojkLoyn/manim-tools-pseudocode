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
        '''rule for pseudocode'''

        rule = {
            "start_marker_pattern": "\(.*\):",
            "start_marker_slice": slice(1, -2),
            "marker_pattern": "\s*###\s*.*\s*"
        }
        rule_ = {
            "start_marker_pattern_compiled":
            re.compile(rule["start_marker_pattern"]),
            "def_str_pattern":
            "\s*def\s*{func_name}%s" % rule["start_marker_pattern"],
        }
        code = {"marker_code_format": "### {marker}"}

        def marker_code(self, marker: str = ""):
            ''' return the code of marker

            parameters:
            marker: str, the marker name

            return:
            str, the code of marker
            '''
            return self.marker_code_format.format(marker=marker)

        def __init__(self):
            '''init the rule'''
            self.__dict__.update(self.__class__.rule)
            self.__dict__.update(self.__class__.rule_)
            self.__dict__.update(self.__class__.code)

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
            ]
            def_str_pattern_compiled = re.compile(
                self.def_str_pattern.format(func_name=func.__name__))
            head = 0
            while def_str_pattern_compiled.fullmatch(
                    pseudocode_sourcelines[head]) is None:
                head += 1
            def_str = pseudocode_sourcelines[head]
            start_marker = self.start_marker_pattern_compiled.search(
                def_str).group()[self.start_marker_slice].strip()

            start_marker_code = self.marker_code(start_marker)

            return [start_marker_code] + pseudocode_sourcelines[head + 1:]

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
        pseudocode_sourcelines = cls.pseudocode_rule().deal_with(
            pseudocode_sourcelines, func)

        source_bytes = json.dumps(pseudocode_sourcelines,
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
        list, the source lines of the pack
        '''
        source_bytes = zlib.decompress(bytes.fromhex(pseudocode_pack_encoded))
        sourcelines = json.loads(source_bytes.decode(encoding))
        return sourcelines

    def __init__(self,
                 origin_pseudocode_pack_encoded: str,
                 warning_update: bool = False,
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

    def _try_warning(self):
        '''try to warn the update and return self'''
        if self._warning_update:
            if not hasattr(self, "_warning_update_info"):
                _warning_update_info = 'need to be updated with: \n{head}"{origin_pack_encoded}"{tail}'.format(
                    head="=" * 8 + "\n",
                    tail="\n" + "=" * 8,
                    origin_pack_encoded=self._origin_pack_encoded)
                self._warning_update_info = _warning_update_info
            warn(self._warning_update_info)
        return self

    @property
    def origin_pack_encoded(self):
        '''return the origin pack encoded'''
        return self._try_warning()._origin_pack_encoded

    @property
    def origin_pack_sourcelines(self):
        '''return the origin pack sourcelines'''
        return self._try_warning().__class__.pack_decode_from(
            self._origin_pack_encoded, encoding=self.encoding)


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
            pack = self.pack_base(source_pack_encoded, warning_update)

        else:
            pack = self.pack_base(dumped_pack_encoded, False)

        return pack


if __name__ == "__main__":

    @pseudocode(
        "789c8b5652008294d434858ccc8c4c8df2fc724dab983c251db03008941455a20a8040767e6a3e8a606a45726a4109a6c2c4e844abc494e258a0442c007b5b19fe"
    )
    def hihi(wow):
        try:
            koeo
        except:
            a[a:ads]

    print(hihi.origin_pack_sourcelines)

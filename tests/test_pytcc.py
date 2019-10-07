import pytest
import pytcc


@pytest.fixture
def tcc():
    return pytcc.TCC()


class TestCompileError:

    exc = pytcc.CompileError('dir/subdir/name.c:123: error: text and more text')

    def test_filename(self):
        assert self.exc.filename == 'dir/subdir/name.c'

    def test_lineno(self):
        assert self.exc.lineno == 123

    def test_type(self):
        assert self.exc.type == 'error'

    def test_text(self):
        assert self.exc.text == 'text and more text'


class TestTcc:

    def test_init_withParams_setsAttributes(self):
        tcc = pytcc.TCC('opt1', 'opt2', options=['opt3'],
                        include_dirs=['incl_dir'],
                        sys_include_dirs=['sys_incl_dir'],
                        library_dirs=['lib_dir'],
                        defines=dict(A='1'), B='2')
        assert tcc.options == ['opt1', 'opt2', 'opt3']
        assert tcc.defines == dict(A='1', B='2')
        assert tcc.include_dirs == ['incl_dir']
        assert tcc.sys_include_dirs == ['sys_incl_dir']
        assert tcc.library_dirs == ['lib_dir']

    def test_run_onCCode_executesMain(self, tcc):
        link_unit = pytcc.CCode("int main(void) { return(123456); }")
        assert tcc.run(link_unit) == 123456

    def test_run_onCFile_loadsFile(self, tcc, tmpdir):
        filename = tmpdir.join('filename.c')
        filename.write("int main(void) { return(123456); }")
        assert tcc.run(pytcc.CFile(str(filename))) == 123456

    def test_run_onStr_loadsFile(self, tcc, tmpdir):
        filename = tmpdir.join('filename.c')
        filename.write("int main(void) { return(123456); }")
        assert tcc.run(str(filename)) == 123456

    def test_run_onMultipleLinkUnits_combinesLinkUnits(self, tcc):
        link_unit1 = pytcc.CCode("extern int f(); int main() {return(f());}")
        link_unit2 = pytcc.CCode("int f() { return(4321); }")
        assert tcc.run(link_unit1, link_unit2) == 4321

    def test_run_onDefines_compilesWithDefines(self, tcc):
        link_unit = pytcc.CCode("int main(void) { return(DEF1 + DEF2); }",
                                {'DEF1': '12'}, DEF2=34)
        assert tcc.run(link_unit) == 12 + 34

    def test_run_onEmptyDefine_setsDefineTo1(self, tcc):
        link_unit = pytcc.CCode("#if DEF!=1\n#error B\n#endif\n"
                                "void main(void) {return;}",
                                DEF=None)
        tcc.run(link_unit)

    def test_run_onLinkUnitsWithDifferentDefines_compilesWithDifferentDefines(self, tcc):
        link_unit1 = pytcc.CCode("#ifdef A\n#error A defined\n#endif", B='1')
        link_unit2 = pytcc.CCode("#ifdef B\n#error B defined\n#endif", A='1')
        link_unit3 = pytcc.CCode("void main(void) { return; }")
        tcc.run(link_unit1, link_unit2, link_unit3)

    def test_run_onTccDefine_compilesWithDefines(self):
        tcc = pytcc.TCC(defines={'DEF1': '12'}, DEF2=34)
        link_unit = pytcc.CCode("int main(void) { return(DEF1 + DEF2); }")
        assert tcc.run(link_unit) == 12 + 34

    @pytest.mark.skip("This feature is not implemented yet")
    def test_run_onLinkUnitDefineOverwritesTccDefine_restoresTccDefineAfterLinkUnit(self):
        tcc = pytcc.TCC(DEF=1)
        link_unit1 = pytcc.CCode("#if DEF!=2\n#error inv. DEF\n#endif", DEF=2)
        link_unit2 = pytcc.CCode("#if DEF!=1\n#error inv. DEF\n#endif")
        link_unit3 = pytcc.CCode("void main(void) { return; }")
        tcc.run(link_unit1, link_unit2, link_unit3)

    def test_run_onTccIncludeDir_ok(self, tmpdir):
        tcc = pytcc.TCC(include_dirs=[str(tmpdir)])
        tmpdir.join('incl.h').write('#define DEF  123')
        link_unit = pytcc.CCode('#include "incl.h"\n'
                                'int main(void) { return(DEF); }')
        assert tcc.run(link_unit) == 123

    def test_run_onTccSysIncludeDir_ok(self, tmpdir):
        tcc = pytcc.TCC(sys_include_dirs=[str(tmpdir)])
        tmpdir.join('incl.h').write('#define DEF  123')
        link_unit = pytcc.CCode('#include "incl.h"\n'
                                'int main(void) { return(DEF); }')
        assert tcc.run(link_unit) == 123

    def test_run_onOptions_ok(self):
        tcc = pytcc.TCC('Werror')
        link_unit = pytcc.CCode('#define REDEF 1\n'
                                '#define REDEF 2\n'    # causes warning
                                'int main(void) { return; }')
        with pytest.raises(pytcc.CompileError):
            tcc.run(link_unit)

    def test_run_onError_passesErrorInCompileErrorExc(self, tcc):
        link_unit = pytcc.CCode("#error ERRORMSG")
        with pytest.raises(pytcc.CompileError, match="ERRORMSG"):
            tcc.run(link_unit)

    @pytest.mark.skip
    def test_build_onWarnings_storesWarningsInBinaryMsgs(self, tcc):
        link_unit = pytcc.CCode('#define REDEF 1\n'
                                      '#define REDEF 2\n'    # causes warning
                                      '#define REDEF 3\n'    # causes warning
                                      'int main(void) { return; }')
        binary = tcc.build(link_unit)
        assert len(binary.msgs) == 2 and 'REDEF' in binary.msgs[0].text

from fmu.dataio.rmscollectors import stratigraphy


def test_define_full_stratigraphy(drogon_project):
    strat = stratigraphy.define_full_stratigraphy(drogon_project)
    print(strat)

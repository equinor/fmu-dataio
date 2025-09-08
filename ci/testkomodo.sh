run_tests () {
    copy_test_files
    start_tests
}

copy_test_files () {
    cp -r $CI_SOURCE_ROOT/tests $CI_TEST_ROOT
    ln -s $CI_SOURCE_ROOT/examples $CI_TEST_ROOT
    # Pytest configuration is in pyproject.toml
    ln -s $CI_SOURCE_ROOT/pyproject.toml $CI_TEST_ROOT/pyproject.toml
    
}

start_tests () {
    pushd $CI_TEST_ROOT
    echo "Testing fmu-dataio against Komodo"
    install_test_dependencies
    run_pytest
    popd 
}

install_test_dependencies () {
    pushd $CI_SOURCE_ROOT
    pip install ".[dev]"
    popd
}

run_pytest () {
    pytest -n 4 -vv 
}
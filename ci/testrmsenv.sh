# This shell script is to be sourced and run from a github workflow
# when fmu-dataio is to be tested towards a new RMS Python environment

run_tests () {
    set_test_variables

    copy_test_files

    install_test_dependencies

    run_pytest
}

set_test_variables() {
    echo "Setting variables for fmu-dataio tests..."
    CI_TEST_ROOT=$CI_ROOT/fmudataio-test-root
}

copy_test_files () {
    echo "Copy fmu-dataio test files to test folder $CI_TEST_ROOT..."
    mkdir -p $CI_TEST_ROOT
    cp -r $PROJECT_ROOT/tests $CI_TEST_ROOT
    cp -r $PROJECT_ROOT/schemas $CI_TEST_ROOT
    cp -r $PROJECT_ROOT/examples $CI_TEST_ROOT
    cp $PROJECT_ROOT/pyproject.toml $CI_TEST_ROOT
}

install_test_dependencies () {
    echo "Installing test dependencies..."
    pip install ".[dev]"
    
    # Reinstall pydantic to force latest version
    pip install -U pydantic

    echo "Dependencies installed successfully. Listing installed dependencies..."
    pip list
}

run_pytest () {
    echo "Running fmu-dataio tests with pytest..."
    pushd $CI_TEST_ROOT
    pytest ./tests -n 4 -vv -m "not skip_inside_rmsvenv" --ignore=tests/test_ert_integration
    popd
}
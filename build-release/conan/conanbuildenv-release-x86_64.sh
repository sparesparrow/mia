script_folder="/home/sparrow/projects/portfolio/mia/build-release/conan"
echo "echo Restoring environment" > "$script_folder/deactivate_conanbuildenv-release-x86_64.sh"
for v in PYTHON_ROOT PATH LD_LIBRARY_PATH PYTHONHOME PYTHONPATH DYLD_LIBRARY_PATH SPARETOOLS_CLI
do
    is_defined="true"
    value=$(printenv $v) || is_defined="" || true
    if [ -n "$value" ] || [ -n "$is_defined" ]
    then
        echo export "$v='$value'" >> "$script_folder/deactivate_conanbuildenv-release-x86_64.sh"
    else
        echo unset $v >> "$script_folder/deactivate_conanbuildenv-release-x86_64.sh"
    fi
done


export PYTHON_ROOT="/home/sparrow/.conan2/p/b/spareb0cd78b74c4e0/p"
export PATH="/home/sparrow/.conan2/p/b/spareb0cd78b74c4e0/p/bin:/home/sparrow/.conan2/p/b/spareb0cd78b74c4e0/p/bin:/home/sparrow/.conan2/p/b/spareb0cd78b74c4e0/p/bin:/home/sparrow/.conan2/p/b/flatbf81590caced44/p/bin:$PATH"
export LD_LIBRARY_PATH="/home/sparrow/.conan2/p/b/spareb0cd78b74c4e0/p/lib:/home/sparrow/.conan2/p/b/spareb0cd78b74c4e0/p/lib:/home/sparrow/.conan2/p/b/flatbf81590caced44/p/lib:$LD_LIBRARY_PATH"
export PYTHONHOME="/home/sparrow/.conan2/p/b/spareb0cd78b74c4e0/p"
export PYTHONPATH="$PYTHONPATH:/home/sparrow/.conan2/p/b/sparecab2724936d27/p:/home/sparrow/.conan2/p/b/spare9c7b9a1667b7a/p:/home/sparrow/.conan2/p/b/spareb0cd78b74c4e0/p/lib/python3.12"
export DYLD_LIBRARY_PATH="/home/sparrow/.conan2/p/b/spareb0cd78b74c4e0/p/lib:/home/sparrow/.conan2/p/b/flatbf81590caced44/p/lib:$DYLD_LIBRARY_PATH"
export SPARETOOLS_CLI="/home/sparrow/.conan2/p/b/sparecab2724936d27/p/cli/main.py"
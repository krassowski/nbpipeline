python3 setup.py install
cd examples
rm -r data/clean
rm -r reports
nbpipeline -d -i
cd ..

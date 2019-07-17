1. Install requirements:

 ```bash
 pip install -r requirements.txt
 ```

2. See `pipeline.py` for the pipeline specification

3. Run nbpipleline:

 ```bash
 nbpipleline --definitions_file pipeline.py --interactive_graph
 ```

 Note:
  - `--definitions_file pipeline.py` can be skipped if the pipeline file is called `pipeline.py`
  - `--interactive_graph` can be shortened to `-i`

4. If you want to play around with the notebooks, run jupyter-lab from this directory:

 ```bash
 jupyter lab
 ```

 Note: when running notebooks manually (not via nbpipeline),
 you will need to create following directories:
 
 ```bash
 mkdir data/clean
 mkdir reports
 ```

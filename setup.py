from setuptools import setup
from setuptools import find_packages


try:
    from pypandoc import convert

    def get_long_description(file_name):
        return convert(file_name, 'rst', 'md')

except ImportError:

    def get_long_description(file_name):
        with open(file_name) as f:
            return f.read()


if __name__ == '__main__':
    setup(
        name='nbpipeline',
        packages=find_packages(),
        scripts=['bin/nbpipeline'],
        version='0.1.11',
        license='MIT',
        description='Snakemake-like pipeline manager for reproducible Jupyter Notebooks',
        long_description=get_long_description('README.md'),
        author='Michal Krassowski',
        author_email='krassowski.michal+pypi@gmail.com',
        url='https://github.com/krassowskinbpipeline',
        keywords=['snakemake', 'pipeline', 'reproducible', 'jupyter', 'notebooks'],
        classifiers=[
            'Development Status :: 4 - Beta',
            'License :: OSI Approved :: MIT License',
            'Operating System :: Microsoft :: Windows',
            'Operating System :: POSIX :: Linux',
            'Topic :: Utilities',
            'Topic :: Software Development :: Libraries :: Python Modules',
            'Intended Audience :: Developers',
            'Intended Audience :: Science/Research',
            'Programming Language :: Python :: 3.6',
            'Programming Language :: Python :: 3.7'
        ],
        install_requires="""
pandas
nbimporter
papermill
pygraphviz
nbstripout
jupyter
ansi2html
networkx
tqdm
declarative_parser
jinja2
nbdime
""".split('\n'),
    )

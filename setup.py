import setuptools

setuptools.setup(
    name='goodtables_pandas',
    version='0.0.1',
    url='https://github.com/ezwelty/goodtables-pandas-py',
    author="Ethan Welty",
    author_email="ethan.welty@gmail.com",
    packages=[
        'goodtables_pandas'
    ],
    install_requires=[
        'pandas',
        'datapackage',
        'goodtables'
    ]
)

import setuptools


setuptools.setup(
    name='django-sql-sniffer',
    version="0.0.1",
    description='Django SQL Sniffer',
    long_description='Minimally invasive analysis of SQL execution in a running process',
    keywords='django sql query remote process analysis',
    url='https://github.com/gruuya/django-sql-sniffer',
    author='Marko Grujic',
    author_email='markoog@gmail.com',
    license='Apache 2.0',
    install_requires=['django>=1.7.0'],
    python_requires='>=3.5',
    packages=['django_sql_sniffer'],
    entry_points=dict(
        console_scripts=[
            'django-sql-sniffer = django_sql_sniffer.listener:main'
        ]
    )
)

import setuptools
import django_sql_sniffer


setuptools.setup(
    name='django-sql-sniffer',
    version=django_sql_sniffer.version,
    description='Django SQL Sniffer',
    long_description='Minimally invasive analysis of SQL execution in a running process',
    keywords='django sql query remote process analysis',
    url='https://github.com/gruuya/django-sql-sniffer',
    author='Marko Grujic',
    author_email='markoog@gmail.com',
    license='MIT',
    install_requires=['django'],
    python_requires='>=3.5',
    packages=['django_sql_sniffer'],
    entry_points=dict(
        console_scripts=[
            'django-sql-sniffer = django_sql_sniffer.listener:main'
        ]
    )
)

Django SQL Sniffer
==================
A simple command line tool for analyzing SQL executed through Django ORM on a running process.
Minimally invasive and granular - no need to change logging config or restart the process.

#Usage
Install though pip
```
pip install django-sql-sniffer
```
Then run the tool by passing it a process id which is to be analyzed
```
django-sql-sniffer -p 76441
```
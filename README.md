Django SQL Sniffer
==================
A simple command line tool for analyzing SQL executed through Django ORM on a running process.
Minimally invasive and granular - no need to change logging config or restart the process.

#Usage
Install though pip
```
pip install django-sql-sniffer
```
To run the tool pass it a process id which is to be analyzed
```
django-sql-sniffer -p 76441
```
`Ctrl + C` to stop and show the query stats summary. `Ctrl + T` to dispay snapshot stats summary without killing the process (only if your OS supports `SIGINFO` signal).
Optionally, setting `-t` flag results in logging queries as they are executed.
By default, sorting is done by max duraton when showing query summary; other options include:
- `-c` for sorting the summary output by query count
- `-s` for sorting the summary output by total combined query duration
- `-n` for setting the number of top query stats to display in summary
- `-v` for verbose logging mode on both the client and server side
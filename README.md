[REDACTED] Script Test v1.1

Purpose: On the [REDACTED] team it’s important to be able to understand, modify, update and contribute to our automation code when necessary. A large portion of our automation code is in Python.

What you’ll need: A Linux OS with Python 2.7 or higher installed.

Expectations: Use any and all resources, just like you would if you were solving the problem for work. We expect to be able to run the script here at [REDACTED] and see your code working. We will also review how you think about the assignment, structure your work and how you communicate/document it. If you are not able to address a requirement please document why. The assignment is to write a Python script that will make system calls and process log files in a way that is similar to what the team writes in their automation today.

1. The Python script you will write will address the following requirements

    a. User input for your script:
        i. Specify a file location and name (example: /root/touchfile.txt)

        ii. Specify how often ( touch rate ) cron will touch the file specified on the input ( example:every 2 minutes)

        iii. Specify a new log roll over file location and prefix, (example:/root/rotate/pythontest)

        iv. Specify how long the script will run (0 for forever, must handle user interrupt in the run forever case)

    b. Using a system call edit the system crontab to touch the file (1.a.i) defined by the touch rate User input field (1.a.ii).

    c. In the following log processing function count the number of times the cron job in requirement (1.b) has touched the file (1.a.i) in the last 7 minutes (you can find and scan cron executions in a log file. (example : ubuntu location of cron executions:/var/log/syslog)
    
        i. Append the date and number of times cron has touched the file (1.a.i) to the file (1.a.i)

        ii. If there are any errors or warnings in syslog in the last 7 minutes, append a timestamp and what was found to the file (1.a.i)

    d. After the file has been touched 15 times, rename the file based on requirement (1.a.iii) with an incremented suffix value. ( This is a log rotate function )

        i. Example of how the file will be renamed from: /root/touchfile.txt to /root/rotate/pythontest.1, /root/rotate/pythontest.2, ...

    e. Handles exceptions appropriately

    f. Returns an exit status for:

        i. success

        ii. error

        iii. user interrupt ( example: CTRL-C )

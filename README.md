DNS & Subdomain Enumeration Tool - README
Introduction
The DNS & Subdomain Enumeration Tool is a Python-based application with a modern PyQt5 graphical interface. It integrates both subdomain enumeration and DNS records analysis into a single tool. The tool is designed to assist cybersecurity students, penetration testers, and researchers in discovering potential attack surfaces by identifying valid subdomains, their DNS records, and checking HTTP/HTTPS responses.
Features
- Subdomain enumeration using a custom wordlist.
- DNS records lookup (A, AAAA, CNAME, MX, TXT).
- HTTP/HTTPS response check to verify live subdomains.
- Progress bar showing the status of the enumeration.
- Results displayed in a dynamic table.
- Dark/Light mode toggle for better usability.
- Export discovered results to a text file.
Requirements
Before running the tool, ensure that the following dependencies are installed:

```bash
pip install requests dnspython PyQt5
```
Usage
1. Save the script as `dns_subdomain_tool.py`.
2. Open a terminal in the directory containing the script.
3. Run the script using:

```bash
python dns_subdomain_tool.py
```

4. Click **'Load Wordlist & Start'** and select your `subdomains.txt` file.
5. The tool will enumerate subdomains, check their DNS records, and verify HTTP/HTTPS response.
6. Use the **Toggle Dark/Light Mode** button to switch UI theme.
7. Save results by clicking **Save Results**.
Example Workflow
Suppose you want to enumerate subdomains for `youtube.com`:

1. Create a file called `subdomains.txt` with entries such as:
```
www
mail
api
dev
```
2. Run the tool and load this file.
3. The discovered subdomains will appear in the results table along with DNS records and response status.
4. Export the results to a text file for documentation.
Output
The tool produces a table with the following columns:
- **Subdomain**: The full discovered subdomain (e.g., mail.youtube.com).
- **DNS Records**: A dictionary of available DNS record types and their values.
- **Status**: Shows whether the subdomain is alive and its HTTP status code.
- **Working URL**: The accessible URL (http/https).

Additionally, the results can be saved into a text file using the 'Save Results' button.

Conclusion

This tool provides a simple yet powerful approach to discovering hidden subdomains and analyzing their DNS records. 
By combining enumeration with a modern GUI and progress tracking, it is highly useful for security assessments and academic research projects.



Screenshots

Figure 1: Main Interface (Dark Mode)

 
Figure 2: Running Subdomain Enumeration with Progress Bar & Discovered Subdomains and DNS Records 


 

Figure 4: Exported Results File Confirmation

 

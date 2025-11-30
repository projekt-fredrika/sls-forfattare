## Intro

A project to use book series **Finland's writers** to improve Wikipedia och Wikidata. 

Described in more detail on project pages: 
* https://sv.wikipedia.org/wiki/Wikipedia:Projekt_Fredrika/SLS-Författare-1809
* https://sv.wikipedia.org/wiki/Wikipedia:Projekt_Fredrika/SLS-Författare-1917
* https://sv.wikipedia.org/wiki/Wikipedia:Projekt_Fredrika/SLS-Författare-1945

## How to use scripts

**Intro:** Vibe coded python script convert publication PDFs to markdown and csv files. Matches writers with existing Wikidata objects, and adds Wikipedia stats for easier prioritization of what Wikipedia articles to work on.

1. Prepare by acquiring scanned books and placing them in folder ```material```

* Suomen kirjailijat 1917-1944.pdf
* Suomen kirjailijat 1945-1980.pdf

2. Set up virtual environement and installing pdfplumber: 

```
python3 -m venv .venv
source .venv/bin/activate
pip3 install pdfplumber
```

3. Move inte desired folder, e.g. ```cd sls-forfattare-1917```

4. Run ```python 01_pdf2md.py``` to convert PDF to markdown file contain entire publication.
* Uses input from 01-files to tweak output: 01_replace.csv, 01_is_header.txt and 01_is_not_header.txt
* In addition to ```01_output.md```, creates for easy debugging: ```01_output_debug.txt```

5. Run ```python 02_md2csv.py``` to create csv file with headers and details.
* Outputs ```02_output.csv```. Import to Google Sheet to easier work on verifying content. 

6. Run ```python 03_add_wikidata.py``` to search Wikidata for author name and add Wikidata Q-code. 
* Use google to search for remaning rows not matched.

7. Run ```python 05_fetchstats.py``` to add Wikipedia article lengths and article views. 
* Start working on actually imporvoing the content! 

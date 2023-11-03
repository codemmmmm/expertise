# Expertise graph

Website for visualizing expertise and more

# Manual

## Search and filter

### Search

* Enter search phrases
* Entities (excluding person names etc.) that contain all of the phrases are matched

### Filter

* Select filters (exact match)
* Using the data returned from the search, every row that fits the filters is shown
* Filters in the same category are ORed, multiple categories are ANDed together
* Exception: person + advisors and offered expertise + wanted expertise count as
    one category each

Filters `Person A, Advisor B, Interest C and Interest D` show all rows where
* the person is A OR an advisor is B AND
* C OR D are among the interests

## Graph

* Click an empty space in the table row to load a graph for that person
* Click a node to traverse the network
* Click + Shift to toggle the filter for that node

# Data guidelines

* Node names that have a commonly used abbreviation should have the abbreviation saved in
    the `alternatives` node property (or the long form as the alternative, if the
    abbreviation is the name)
* The same phrase should always be abbreviated or typed out (e.g. always "AI")
* American English probably
* Everything capitalized besides "stop words" and verbs after a "-"
* A person should be connected to a **topic of interest's** major supergroup, if they are
    connected to a supergroup
  * e.g. if connected to "Explainable AI" they should also be connected to "AI"
  * other supergroups are "ML", "Big Data", "Optimization"
  * currently isn't done for expertise, but might be done later
* Institutions: the university, other major companies, ...
* Faculties: university institutes, university faculties, centers, ...
  * "Institute ..." not abbreviated
* Department: groups, departments, ...
* Not many new roles should be entered

## Change label (category) names

* table headers in index.html
* "group_name" in get_suggestions() in views.py
* form field labels and helptext in forms.py

# Installation

for Apache 2.4, Java 11, Neo4j 4.4 on Ubuntu 22 and installing the project in /home/$USER/

## Steps

1. Clone the repository -> `~/expertise` exists
2. Install some things
    ```
    sudo apt-get update
    sudo apt install python3.10-venv python3-dev apache2 apache2-dev openjdk-11-jre-headless
    ```

3. Install Neo4j

    the apt-key command is used because the commands using the non-deprecated trusted.gpg way didn't work (yet)
    ```
    wget -O - https://debian.neo4j.com/neotechnology.gpg.key | sudo tee /etc/apt/keyrings/neotechnology.gpg
    echo 'deb [signed-by=/etc/apt/keyrings/neotechnology.gpg] https://debian.neo4j.com stable 4.4' | sudo tee -a /etc/apt/sources.list.d/neo4j.list
    sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 59D700E4D37F5F19
    sudo apt-get update
    sudo apt-get install neo4j=1:4.4.21
    sudo systemctl enable --now neo4j
    ```

4. Setup Neo4j

    Run `cypher-shell`, login with user: neo4j and password: neo4j and set and
    remember a username and password.

5. Create and activate a python virtual environment

    ```
    python3 -m venv ~/expertise/venv
    source ~/expertise/venv/bin/activate
    ```

6. Install python packages

    ```
    pip3 install --upgrade pip
    pip3 install wheel
    pip3 install mod_wsgi
    pip3 install -r ~/expertise/requirements.txt
    pip3 install Django==4.2
    ```

7. Set environment variables

    Generate a secret key for django using `python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'`.

    Write these commands into `~/.bashrc` and `/etc/apache2/envvars`, replacing the NEO4J_USER, NEO4J_PASSWORD and KEY.
    ```
    export NEO4J_BOLT_URL='bolt://NEO4J_USER:NEO4J_PASSWORD@localhost:7687/neo4j'
    export DJANGO_SECRET_KEY='KEY'
    export DJANGO_LOG_LEVEL='INFO'
    ```

    Then run
    ```
    source ~/.bashrc
    source ~/expertise/venv/bin/activate
    ```

8. Configure Apache and Django, replacing USER with your $USER.

    ```
    mod_wsgi-express module-config | sudo tee /etc/apache2/mods-available/wsgi.load
    sudo a2enmod wsgi
    sudo usermod -a -G USER www-data
    ```

    Write this into `/etc/apache2/apache2.conf`
    ```
    Alias /static/ /home/USER/expertise/mysite/static/

    <Directory /home/USER/expertise/mysite/static>
    Require all granted
    </Directory>

    WSGIScriptAlias / /home/USER/expertise/mysite/mysite/wsgi.py
    WSGIPythonHome /home/USER/venv/expertise
    WSGIPythonPath /home/USER/expertise/mysite
    WSGIApplicationGroup %{GLOBAL}

    <Directory /home/USER/expertise/mysite/mysite>
    <Files wsgi.py>
    Require all granted
    </Files>
    </Directory>
    ```

    Edit the `~/expertise/mysite/mysite/settings.py` and replace SERVER_IP.
    ```
    ALLOWED_HOSTS = ['.localhost', '127.0.0.1', '[::1]', SERVER_IP]
    STATIC_ROOT = '/home/USER/expertise/mysite/static/'
    ```

    Run
    ```
    python3 ~/expertise/mysite/manage.py collectstatic
    python3 ~/expertise/mysite/manage.py install_labels
    python3 ~/expertise/mysite/manage.py migrate
    chmod g+w mysite/db.sqlite3
    ```

9. Create the directory `/home/USER/expertise/mysite/log/`, replacing USER.

10. Load the database from a dump as the Neo4j user.

    ```
    sudo su - neo4j -c "neo4j-admin load --from=file.dump --force"
    ```

11. HTTPS using certbot (MAYBE LATER, NOT CURRENTLY)

    ```
    sudo apt install snap
    sudo snap install core; sudo snap refresh core
    sudo snap install --classic certbot
    sudo ln -s /snap/bin/certbot /usr/bin/certbot
    sudo certbot --apache
    sudo certbot renew --dry-run
    ```

12. Create a superuser `python ~/expertise/mysite/manage.py createsuperuser`. Log in
    to the admin page, create a group with permissions for edit submissions.
    Create users and assign that group so they can approve.

# Build

The css needs to be built when Bootstrap variables need to be changed. Install npm,
the dependencies of the project and do `npm run build`.

# Updating

1. Stash changes if needed. Then get the changes with `git pull`.

2. Apply the stashed changes. Set STATIC_ROOT and ALLOWED_HOSTS as seen in installation,
    if necessary. Then run
    ```
    python3 ~/expertise/mysite/manage.py makemigrations
    python3 ~/expertise/mysite/manage.py install_labels
    python3 ~/expertise/mysite/manage.py migrate
    python3 ~/expertise/mysite/manage.py collectstatic
    sudo systemctl restart apache2
    ```

# Troubleshoooting

* Make sure the static files were collected after updating them.
* Make sure the apache user is part of the user's group in whose home directory django is.
* Make sure `mysite/db.sqlite3` has write permissions for the group.


# Limitations

Neo4j Community Edition only supports only one database per server

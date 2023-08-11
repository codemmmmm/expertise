# Expertise graph

Website for visualizing expertise after converting the data

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

    Run `cypher-shell`, login with user: neo4j and password: neo4j and set and remember a username and password.

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
    ```

9. Convert the CSV data using `python3 ~/expertise/convert/convert.py CSV_FILE`.

10. HTTPS using certbot

    ```
    sudo apt install snap
    sudo snap install core; sudo snap refresh core
    sudo snap install --classic certbot
    sudo ln -s /snap/bin/certbot /usr/bin/certbot
    sudo certbot --apache
    sudo certbot renew --dry-run
    ```

11. Create a superuser `python manage.py createsuperuser`. Log in to the admin page,
    create a group with permissions for edit submissions and create users for that group
    so they can approve.

# Limitations

Neo4j Community Edition only supports only one database per server

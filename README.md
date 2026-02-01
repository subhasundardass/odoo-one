# Odoo with one command.
``
Some arguments: Update

- First argument (**odoo-one**): Odoo deploy folder
- Second argument (**10017**): Odoo port
- Third argument (**20017**): live chat port

If `curl` is not found, install it:

```bash
$ sudo apt-get install curl
# or
$ sudo yum install curl
```

## Usage

Start the container:

```sh
docker-compose up
```

Then open `localhost:10017` to access Odoo 17.

- **If you get any permission issues**, change the folder permission to make sure that the container is able to access the directory:

```sh
$ sudo chmod -R 777 addons
$ sudo chmod -R 777 etc
$ sudo chmod -R 777 postgresql
```

- If you want to start the server with a different port, change **10017** to another value in **docker-compose.yml** inside the parent dir:

```
ports:
 - "10017:8069"
```

- To run Odoo container in detached mode (be able to close terminal without stopping Odoo):

```
docker-compose up -d
```
## Custom addons

The **addons/** folder contains custom addons. Just put your custom addons if you have any.

## Odoo configuration & log

- To change Odoo configuration, edit file: **etc/odoo.conf**.
- Log file: **etc/odoo-server.log**

## Odoo container management 2

**Run Odoo**:

```bash
docker-compose up -d
```

**Restart Odoo**:

```bash
docker-compose restart
```

**Stop Odoo**:

```bash
docker-compose down
```

## Live chat

In [docker-compose.yml#L21](docker-compose.yml#L21), we exposed port **20017** for live-chat on host.

Configuring **nginx** to activate live chat feature (in production):

```conf
#...
server {
    #...
    location /longpolling/ {
        proxy_pass http://0.0.0.0:20017/longpolling/;
    }
    #...
}
#...
```

## docker-compose.yml

- odoo:17
- postgres:16


## HELP

docker exec -it odoo-one-odoo17-1 odoo -d odoo17 -u all --db_host=db --db_user=odoo --db_password='odoo17@2023' --stop-after-init
# postgres
docker exec -it odoo-one-db-1 psql -U odoo -d postgres
# odoo bash
docker exec -it odoo-one-odoo17-1 bash
# python 
odoo shell -d odoo17


## Team Git Rule
1. main - production, stable, release code
2. feature-dev - final test with all module and functions 
3. sit-dev - integration and testing 

*Developer workflow
1. git checkout your_branch
2. git fetch origin
3. git merge origin/sit-dev ( fix conflicts if any)
4. git push origin your_branch

Then raise PR
Source: sit-dev
Compare: your_branch

Note
Ignore conflicts resolve at GitHub, do it locally
# Liaison

Liaison was an email communication platform. It allowed users to create or upload html content and handled delivery to customers. The defining ability was the automatic adjustment of email headers to send on behalf of 3rd parties, which is critical to a business model seeking a client facing email from a personalized sales force. It was also highly dynamic to allow for varying customer data and content which would be imported into the system.

What you see here is a stripped down version of the platform that could be used as an example for other projects. After the conclusion of this project, Mandrill dramatically changed how it operates the rendering it useless as an email delivery service. A similar provider like Sendgrid or Mailgun could be used instead. Most aspects, especially the provisioning, would need significant updates to work in a different environment than what was originally setup.

Tech Stack:

* Web servers: Python, Flask
* Queuing: RabbitMQ
* Async background tasks: Celery and Celery Beat
* DB: Postgresql

Hosting:

* AWS deployed via Ansible
* Web/Queue/Celery servers on EC2
* DB on RDS


## Commands

* Run the server
	* `python run.py`
	* or `gunicorn -w 2 -b 127.0.0.1:4000 liaison:app`
* Celery
	* `celery -A liaison.lib.tasks.celery worker -l info -P processes -c 10 -f {log_dir}/celery.log -Q dispatcher,default,mail,beat`
* Celery Beat
	* `celery -A liaison.lib.tasks.celery beat -l info -f {log_dir}/beat.log`
* Flower
	* `flower --port=5555 -A liaison.lib.tasks.celery`
* Rabbit MQ
	* `rabbitmq-server` or `rabbitmq-server -detached`
	* `rabbitmqctl list_queues`
	* `rabbitmqctl stop`


## Installation

* `brew install`
    * `rabbitmq`
    * `postgresql`
* create database liaison in postgresql
* `mkdir {log_dir}`
* `git clone ...`
* `cd liaison`
* `mkvirtualenv liaison`
* `pip install -r requirements.txt`
* `python manage.py db upgrade`
* `python run.py`
* run rabbitmq and celery as needed


## Provisioning

From the /provisioning directory

* ansible-galaxy install -r requirements.txt --ignore-errors
* (vagrant) You will have to add a :2841 to the inventory IP's after you provision the first time.

AWS - from provisioning directory

* `ansible-playbook -i inventories/ec2.py -v aws.yml`
* `ansible-playbook -i inventories/ec2.py -v web.yml --vault-password-file $DIR/vault_file.txt`
* `ansible-playbook -i inventories/ec2.py -v web.yml --vault-password-file $DIR/vault_file.txt --tags deploy`

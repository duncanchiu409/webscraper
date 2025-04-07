# A Free Web Scraper on Github Actions Sample saving to DynamoDB
## Overview

This is a sample project that demonstrates how to create a free web scraper using Github Actions. The python script interacts with the docker container of the webdriver. On github actions, I have written a workflow file to run the python script using docker-compose.yml and save the results to AWS DynamoDB.

## Context

1. Setup
2. How the Python script works
3. Testing on Local
4. How the Github Actions works
5. Design Consideration

## Setup

Please make you have installed docker and aws cli. Docker (https://docs.docker.com/engine/install/) is used to run the webdriver and aws cli (https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) is used to save the results to DynamoDB. The my development os is ubuntu 24.04 LTS so I assume the same for you.

### Setup Docker

First, we need to pull the docker image of the webdriver. I used selenium/standalone-chrome-debug:latest instead of selenium/grid-hubs and selenium/node-chrome:latest because I don't need to run the webdriver on multiple browsers. (https://hub.docker.com/r/selenium/standalone-chrome)

```bash
docker pull selenium/standalone-chrome:latest
```

Next, we need to start the docker container.

```bash
docker run -d -p 4444:4444 -p 7900:7900 -v /dev/shm:/dev/shm selenium/standalone-chrome:latest
```

### Setup AWS DynamoDB

First, we need to create a IAM user with the full access to DynamoDB. Creating the user in the AWS console following this guide. (https://docs.aws.amazon.com/IAM/latest/UserGuide/id_users_create.html)

#### Creating the user in the AWS IAM console

To create an IAM user with full access to DynamoDB, navigate to the IAM service in the AWS console, create a new user named "webscraper-user", attach the "AmazonDynamoDBFullAccess" policy, and generate access keys. Optionally, you can add tags like "webscraper" to the user for better organization. Please note that we need to import the credentials to the AWS CLI and Github Actions so please save the credentials.csv file.

#### Import the credentials to AWS CLI

Add a Column "User Name" and value "webscraper-user" (my user name) to the credentials.csv file and run the command below to import the credentials.

```bash
aws configure import --profile <your-profile-name> --csv file://<complete-path-to-credentials.csv>/credentials.csv
```

Note that if you encounter the error "Expected header "User Name" not found in file" please add a "User Name" column to the credentials.csv file. Helpful link: (https://github.com/aws/aws-cli/issues/7721)

#### Create a DynamoDB table
You can either create the table in the AWS console or using the aws cli. I will show you how to create the table using the aws cli. (https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/getting-started-step-1.html)

The command below creates a table with the name "coinmarketcap-trending-ranking-table" and the primary key "id" where id is the coinmarketcap's trending ranking id in string format according to the profile and region you have set.

```bash
aws dynamodb create-table --table-name webscraper-coinmarketcap-trending-ranking-table \
    --attribute-definitions AttributeName=id,AttributeType=S \
    --key-schema AttributeName=id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --table-class STANDARD --profile <your-profile-name> --region <your-region>
```

Noted that: There are two billing modes for DynamoDB. The default is on-demand mode and the other is provisioned mode. I recommend you to use on-demand mode because it is more flexible and you don't need to set the read and write capacity units. Helpful link: (https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/capacity-mode.html#capacity-mode-on-demand)

To check if the table is created, run the command below. You should see the table name in the output in a json format.

```bash
aws dynamodb list-tables --profile <your-profile-name> --region <your-region>
```

Example output:

```json
{
    "TableNames": [
        "webscraper-threads-posts-table"
    ]
}
```

### Setup Python

Firstly, we need to create a virtual environment. My python version is 3.10.4 so I will use python 3.10 to create the virtual environment.

```bash
python -m venv venv
```

Then, we need to activate the virtual environment.

```bash
source venv/bin/activate
```

To check if the virtual environment is activated, run the command below. You should see the venv in the output.

```bash
which python
```

Example output:

```bash
/home/ubuntu/webscraper/venv/bin/python
```

Next, we need to install the dependencies. The requirements.txt file is included in my repository if you want more dependencies you can first install the dependencies in the requirements.txt file, install your own dependencies and run `python -m pip freeze > requirements.txt` to update the requirements.txt file.

```bash
pip install -r requirements.txt
```

## Python Script
The python script is in the src/coinmarketcap_webscraper.py file. For a web-scraper to work, there are some steps that we need to follow.

1. Initialize the webdriver
2. Login to the website
3. Scrape the website
4. Scroll to the bottom of the page
5. Repeat from 3.
6. Save the results to DynamoDB

I will show you a demo of the python script that I used to scrape the coinmarketcap's trending ranking:

### Initialize the webdriver
To initialize the webdriver, we need to import the webdriver from the selenium package. We can either use the chrome webdriver or the firefox webdriver. I will use the chrome webdriver in this example. Moreover, we can choose whether to use remote webdriver or local webdriver. I will use the remote webdriver in this example.

```python
from selenium import webdriver

options = webdriver.ChromeOptions()
options.add_argument("--no-sandbox")
options.add_argument("--headless=new")
options.add_argument("--disable-dev-shm-usage")

driver = webdriver.Remote(
    command_executor='http://localhost:4444',
    options=options
)
```

Noted that if you want to view the webdriver in action, please comment out `options.add_argument("--headless=new")`, you can open the http://localhost:7900/?autoconnect=1&resize=scale&password=secret to view the webdriver in action.

There are some Chrome options that we can set. For example, we can set the headless mode to true if we want to run the webdriver in the background. I listed some of the Chrome options below from the selenium documentation: (https://selenium-python.readthedocs.io/api.html#module-selenium.webdriver.chrome.options)

```python
options.add_argument("--headless=new")
options.add_argument('--no-sandbox')
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1280x1696")
options.add_argument("--single-process")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-dev-tools")
options.add_argument("--no-zygote")
# Credit to https://github.com/umihico/docker-selenium-lambda/blob/main/main.py
# Useful Reference: https://aws.amazon.com/blogs/devops/serverless-ui-testing-using-selenium-aws-lambda-aws-fargate-and-aws-developer-tools/
```

Noted that if you use the remote webdriver in a Docker container, you need run the initialize webdriver function in a while loop until the webdriver is initialized. It is because the webdriver is not initialized immediately when the container is started. see in https://stackoverflow.com/questions/59938479/how-to-solve-problems-with-urllib3-connectionpool-used-in-selenium-when-parallel

### Scrape the website
After the webdriver get the page_source, I have parse the page_source into `BeautifulSoup`. I didn't not use the default html parse library because it is not as consistent as `BeautifulSoup`.

To detect the webdriver has loaded the page, you can use `time.sleep(5)` to wait for the page to be loaded. However, it is not safe, I used the wait_for_element function to wait for the element to be present in the page. The wait_for_element function is defined below.

```python
def wait_for_element(driver, xpath, timeout=5):
    WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.XPATH, xpath)))
```

Note that I ran into the problem that the webdriver is not quit() or close() when the I put it in the end of the script. Therefore, I put "with" after the driver initialization and interaction with the webdriver as above. see in https://github.com/SeleniumHQ/selenium/issues/8571

When the code execution is out of the `with` statement, the webdriver will be quit() or close(). This is a example of the `with` statement:

```python
with driver:
    driver.get(url)
    soup = BeautifulSoup(driver.page_source, 'html5lib')
```

### Scroll to the bottom of the page
If you have a website that is on scrolling instead of page pagination, you can scroll to the bottom of the page by using the execute_script method of the driver.

```python
driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
```

If you want the webdriver to scroll to the bottom of the page smoothly, you can use the `smooth behavior` in the Chrome. see in https://developer.mozilla.org/en-US/docs/Web/API/Element/scrollTo

```python
driver.execute_script("window.scrollTo({top:document.body.scrollHeight, behavior:'smooth'})")
```

### Save the results to DynamoDB
I save the results to DynamoDB by using the put_item method of the dynamodb client.

```python
# Localhost
session = boto3.Session(profile_name=self.profile_name)
dynamodb_client = session.resource('dynamodb', region_name=self.region_name)
table = dynamodb_client.Table(self.table_name)
table.put_item(Item=item)

# Github Actions
dynamodb_client = boto3.resource('dynamodb', region_name=self.region_name)
table = dynamodb_client.Table(self.table_name)
table.put_item(Item=item)
```

Apparently, if you are using IAM user with AWS Github Actions, you will be using the default profile. Therefore, you need to set the profile name to the boto3 session on localhost. If you are using multiple profiles, you can set the profile name to the boto3 session on Github Actions by see in https://github.com/aws-actions/configure-aws-credentials/issues/112

```
- name: Add profile credentials to ~/.aws/credentials
   env:
      AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
      AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
   run: |
      aws configure set aws_access_key_id $AWS_ACCESS_KEY_ID --profile my-app-name
      aws configure set aws_secret_access_key $AWS_SECRET_ACCESS_KEY --profile my-app-name
```

## Testing on Local
You can open the http://localhost:7900/?autoconnect=1&resize=scale&password=secret to view the webdriver in action.

## How the Github Actions works
I have written a workflow file to run the python script and save the results to DynamoDB. The workflow file is in the .github/workflows/scrape.yml file. I have used the `schedule` to run the workflow every day at 8:15 AM or trigger the workflow manually (`workflow_dispatch`). (https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#scheduled-events)

```yaml
name: Scrape CoinMarketCap

on:
  workflow_dispatch:
  schedule:
    - cron: "15 8 * * *"

jobs:
  Scrape:
    runs-on: ubuntu-latest
    environment: Credentials
    steps:
      - uses: actions/checkout@v2

      - name: Create credentials folder
        run: mkdir src/credentials

      - uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-region: ${{ secrets.AWS_REGION }}
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}

      - name: Pull Docker image
        run: docker pull selenium/standalone-chrome:latest

      - name: Start up Standalone-Chrome docker container
        run: docker run -d -p 4444:4444 -p 7900:7900 --shm-size="2g" selenium/standalone-chrome:latest

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10.4'
          architecture: 'x64'

      - name: Create .env file
        run: |
          touch src/.env
          echo AWS_REGION=${{ secrets.AWS_REGION }} >> src/.env
          echo COIN_MARKET_CAP_TABLE_NAME="webscraper-coinmarketcap-trending-ranking-table" >> src/.env
          echo COIN_MARKET_CAP_URL="https://coinmarketcap.com/trending-cryptocurrencies/" >> src/.env
          echo TIMEZONE="Asia/Hong_Kong" >> src/.env

      - name: Install dependencies
        run: pip install -r src/requirements.txt

      - name: Scrape CoinMarketCap
        run: python src/coinmarketcap_webscraper.py

      - name: Stop Standalone-Chrome docker container
        run: docker stop $(docker ps -q)
```

## Design Consideration
There are plenty of program architecture to choose from. For example, we can run the Selenium webdriver in AWS Lambda or AWS Fargate. However, I choose to run the Selenium webdriver in Github Actions because it is more flexible and easier to manage.

The first thing that come to my mind if we use AWS lambda or AWS Fargate is that we need to manage the lambda function or the Fargate task. There is no easy pipleline to manage CI/CD to run the lambda function or the Fargate task. To setup the pipeline, we need to setup the AWS CodeCommit and AWS CodePipeline services.

The second thing is that the Github Actions is more flexible and easier to manage. If we use AWS lambda or AWS Fargate, in order to manage the cron job, we need to setup AWS EventBridge to trigger the lambda function or the Fargate task.

The third and most important thing is that Github Actions is free for public repositories. If we use AWS lambda or AWS Fargate, we need to pay for the lambda function or the Fargate task.
# SCALE
Serverless Chat Architecture for LLM Experiments (with an application to oTree)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) [![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/) [![AWS Lambda](https://img.shields.io/badge/AWS-Lambda-orange.svg)](https://aws.amazon.com/lambda/) [![oTree](https://img.shields.io/badge/oTree-5.0+-green.svg)](https://www.otree.org/) [![OpenAI](https://img.shields.io/badge/OpenAI-API-412991.svg)](https://openai.com/)

**Authors:** Sebastian Valet, Johannes Walter

## Table of Contents

- [SCALE](#scale)
  - [Table of Contents](#table-of-contents)
  - [Introduction](#introduction)
    - [Architecture](#architecture)
    - [Alternatives](#alternatives)
  - [Setup](#setup)
    - [Lambda Function Setup](#lambda-function-setup)
  - [Key Lambda Function Files](#key-lambda-function-files)
  - [oTree Implementation](#otree-implementation)
  - [Application examples](#application-examples)
  - [Attribution](#attribution)
  - [References](#references)

## Introduction

Online experiments involving chat interactions between participants and large language models (LLMs) are gaining popularity in the social sciences. Yet running these experiments at scale poses technical challenges.

While the [oTree framework](https://www.otree.org/) is widely used for online behavioral experiments, it struggles with handling many concurrent requests. This is primarily because oTree is single-threaded and not optimized for high-throughput API interactions, leading to performance bottlenecks. These limitations can cause sluggish responses, a poor user experience, and increased server costs.

To address this, we use [AWS Lambda](https://aws.amazon.com/lambda/), a serverless compute service that lets you run backend code without managing servers. It’s easy to set up, scalable, and includes a free tier suitable for many academic experiments.

### Architecture

Our architecture uses:

- **oTree** for the experiment back-end and front-end.
- **AWS Lambda** to handle the chat between participant and AI.

The participant’s browser sends API requests to Lambda for LLM interactions, offloading the heavy lifting from the oTree server.

### Alternatives

- [Chopra et al. (2023)](https://arxiv.org/abs/2309.06419) use Qualtrics for LLM interviews.
- [McKenna (2023)](https://github.com/clintmckenna/oTree_gpt) integrates LLMs directly into the oTree back-end.

Our approach is modular and more scalable — compatible with many platforms beyond oTree.

## Setup

The setup includes AWS configuration, deployment via AWS SAM, and integration with oTree. Scripts automate most of the process:

- `a_init.sh`: Initializes resources like S3 and DynamoDB.
- `b_deploy.sh`: Deploys the Lambda function.

AWS free tier (as of writing):

- **Lambda**: 1M free requests and 400,000 GB-seconds/month.
- **DynamoDB**: 25GB storage, 25 RCU + 25 WCU.

To avoid unexpected charges when exceeding free tier limits, consider setting up billing alerts in the AWS Console and monitoring usage through CloudWatch metrics during active experiments.

### Lambda Function Setup

1. **Create AWS Account and IAM User**

   - Permissions needed:
     - `AmazonS3FullAccess`
     - `AmazonDynamoDBFullAccess`
     - `AWSCloudFormationReadOnlyAccess`
     - `IAMFullAccess`
     - `AWSLambda_FullAccess`

2. **Install Prerequisites**

   - [Docker Desktop](https://www.docker.com/products/docker-desktop/) – Required to build and run Lambda functions locally.
   - [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html) – To interact with AWS services via the command line.
   - [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html) - For building, testing, and deploying serverless applications.
   - Terminal for Windows users:
     - [WSL (Ubuntu 22.04)](https://learn.microsoft.com/en-us/windows/wsl/install) or [Git Bash](https://gitforwindows.org/)

3. **Clone the Repository**

   - Fork or clone this repository to your local machine.

4. **Configure and Run `a_init.sh`**

   ```bash
   bash a_init.sh --aws-access-key-id <YOUR_KEY> --aws-secret-access-key <YOUR_SECRET>
   ```

5. **Configure and Run `b_deploy.sh`**

   - Ensure Docker Desktop is running. You’ll also need your OpenAI API key:

   ```bash
   bash b_deploy.sh --openai-api-key <YOUR_OPENAI_API_KEY>
   ```

6. **Note the API Gateway Endpoint**

   - This URL allows the participant’s front-end to send chat requests.

⚠️**Security Note:** This setup exposes the API Gateway endpoint in the front-end JavaScript, making it publicly accessible. Anyone who knows the endpoint URL can send requests to your Lambda function. To mitigate potential misuse:

- A CORS policy restricts access to the API to requests from the oTree front-end origin.
- API Gateway is rate-limited to 15 requests per second.
- Limits for messages sent per chat, and new chats started per `user_id` (see `main.py`).
- You can restrict access to specific user IDs by specifying an allowlist in `user_config.py`.

For temporary deactivation between experiments, set the Lambda function’s concurrency to 0 under *Configuration → Concurrency and recursion detection* in the AWS Console. This blocks execution without requiring redeployment.

## Key Lambda Function Files

- **`lambda.py`**: Entry point. Handles API Gateway routes:
  - `initialize`: Start a new chat session
  - `chat`: Send user message, receive AI response
  - `history`: Get full chat history
- **`main.py`**: Core logic:
  - Manages chat state with DynamoDB
  - Sends messages to GPT-4o via OpenAI API
  - Can be customized (model, tokens, system prompt)

## oTree Implementation

We use the `oTree-template` repo as a starting point. To use:

1. Navigate to the `otree-template` directory.
2. Set the `AWS_LAMBDA_API_ENDPOINT` environment variable.
3. Edit system prompts in `chat/__init__.py` (class `chat(Page)`).
4. Run development server with `otree devserver`

💡 The oTree backend does not call the Lambda. API calls are done in the front-end (`chat.html` + `chat.js`) to avoid concurrency issues. Be aware that this means that oTree variables such as `participant.code` are passed to the front-end as a `js_vars` object.

## Application examples

Coming soon to a paper near you!

## Attribution

If you use our implementation, please cite our technical report:

```text
Valet, Sebastian, Walter, Johannes D. 2025. SCALE - Serverless Chat Architecture for LLM Experiments. Available at https://github.com/svalet/SCALE.
```

or

```bibtex
@misc{valet-2025-scale,
    author = {Sebastian Valet and Johannes Walter},
    title = {SCALE - Serverless Chat Architecture for LLM Experiments},
    year = {2025},
    note = {Available at https://github.com/svalet/SCALE}
}
```

If you are using the oTree implementation, make sure to also site their paper (see their [website](https://otree.readthedocs.io/en/master/install.html)).

## References

- Chen, Daniel L., Martin Schonger, and Chris Wickens. 2016. “oTree—An open‐source platform for
  laboratory, online, and field experiments.” Journal of Behavioral and Experimental Finance 9:
  88–97.
- Chopra, Felix, and Ingar Haaland. 2023. “Conducting Qualitative Interviews with AI.” CESifo Working Paper No. 10666.
- McKenna, Clint. 2023. “oTree GPT.” Available at https://github.com/clintmckenna/oTree_gpt.

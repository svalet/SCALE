#!/bin/bash

set -e

#############################################################################
# AWS Deploy Script for OpenAI Chat Lambda Function
#
# This script deploys your Lambda function to AWS using the Serverless
# Application Model (SAM). It performs two main tasks:
#   1. Builds your Lambda package (including dependencies)
#   2. Deploys the package to AWS, creating/updating all necessary resources
#
# Prerequisites:
#   - AWS CLI configured (run a_init.sh first)
#   - AWS SAM CLI installed
#   - Docker installed (used by SAM for building)
#   - S3 bucket created (from a_init.sh)
#   - DynamoDB table created (from a_init.sh)
#############################################################################

# Configuration constants
BUCKET_NAME="scale-lambda-deployment"
TABLE_NAME="scale_chats"
ALLOWED_PROD_ORIGIN="https://production-origin.com"

# Parse command line arguments - only for OpenAI API key
while [[ $# -gt 0 ]]; do
  case $1 in
    --openai-api-key)
      OPENAI_API_KEY="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      echo "Valid option: --openai-api-key <KEY>"
      exit 1
      ;;
  esac
done

# Display configuration
echo "AWS Deploy Script"
echo "----------------"
echo "Using configuration:"
echo "  Bucket: $BUCKET_NAME"
echo "  Table:  $TABLE_NAME"
echo

# Validate that all required parameters are provided
if [ -z "$OPENAI_API_KEY" ]; then
    echo "Error: OpenAI API key cannot be empty!"
    echo "Provide it with --openai-api-key <KEY> or set OPENAI_API_KEY environment variable"
    exit 1
fi

#############################################################################
# STEP 1: Build the Lambda function package
# 
# What happens during build:
# - SAM creates a temporary build directory (.aws-sam)
# - Python dependencies from requirements.txt are installed
# - All necessary code and dependencies are packaged together
# - Docker ensures compatibility with the Lambda environment
#############################################################################
echo "Building application including local changes..."
sam build --use-container 
echo "Build step completed."

#############################################################################
# STEP 2: Deploy the Lambda function to AWS
#
# What happens during deployment:
# - Your code package is uploaded to the specified S3 bucket
# - AWS CloudFormation creates or updates the necessary resources:
#   * Lambda function to run your code
#   * API Gateway to provide HTTP access
#   * IAM roles for proper permissions
#   * Connections to your DynamoDB table
# - Your OpenAI API key is securely stored as a Lambda environment variable
#############################################################################
echo "Deploying to cloud using provided S3 bucket, Dynamo table, and OpenAI API key..." 
sam deploy \
    --parameter-overrides TableName=$TABLE_NAME OpenAIApiKey=$OPENAI_API_KEY  AllowedOrigin=$ALLOWED_PROD_ORIGIN\
    --no-confirm-changeset \
    --no-fail-on-empty-changeset \
    --s3-bucket $BUCKET_NAME
echo "Deployment step completed."

#############################################################################
# Deployment Summary
#
# The API Gateway endpoint shown above is your function's public URL.
# This is the address where you'll send requests to interact with your
# Lambda function.
#
# Example test request using curl:
# curl -X POST https://[your-api-id].execute-api.[region].amazonaws.com/Prod/ \
#      -H 'Content-Type: application/json' \
#      -d '{"route": "initialize", "payload": {
#          "chat_id": "chat-1",
#          "user_id": "user-1",
#          "system_message": "You are a helpful assistant."
#      	}}'
#############################################################################

echo "Deployment successful!"
echo "Look for the API Gateway endpoint in the output above - this is your function's URL."
echo "Remember this URL for making requests to your Lambda function."
#!/bin/bash

set -e

#############################################################################
# AWS Setup Script for OpenAI Chat Lambda Function
#
# This script configures your AWS environment for deploying a serverless
# application. It performs these tasks based on the activation flags:
#   - Configure AWS CLI with credentials (if provided)
#   - Create S3 bucket for deployment packages
#   - Create DynamoDB table for chat data
#
# Prerequisites:
#   - AWS CLI installed (aws --version)
#   - AWS SAM CLI installed (sam --version)
#   - AWS account with appropriate permissions
#############################################################################

# Configuration constants
AWS_REGION="eu-central-1"
BUCKET_NAME="scale-lambda-deployment"
TABLE_NAME="scale_chats"

# Action flags - set which parts of the script to run
DO_CONFIGURE_AWS=true
DO_CREATE_BUCKET=true
DO_CREATE_TABLE=true

# Parse command line arguments for API keys only
while [[ $# -gt 0 ]]; do
  case $1 in
    --aws-access-key-id)
      AWS_ACCESS_KEY_ID="$2"
      shift 2
      ;;
    --aws-secret-access-key)
      AWS_SECRET_ACCESS_KEY="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      echo "Valid options:  --aws-access-key-id <KEY> --aws-secret-access-key <SECRET>"
      exit 1
      ;;
  esac
done

echo "AWS Setup Script"
echo "----------------"
echo "Using configuration:"
echo "  Region: $AWS_REGION"
echo "  Bucket: $BUCKET_NAME"
echo "  Table:  $TABLE_NAME"
echo

#############################################################################
# STEP 1: Configure AWS CLI with credentials
# This allows subsequent AWS commands to authenticate properly
#############################################################################
if [[ "$DO_CONFIGURE_AWS" == "true" ]]; then
  if [[ -z "$AWS_ACCESS_KEY_ID" || -z "$AWS_SECRET_ACCESS_KEY" ]]; then
    echo "Warning: AWS credentials not provided. Skipping AWS CLI configuration."
    echo "Make sure your AWS CLI is already configured or provide credentials with --aws-access-key-id and --aws-secret-access-key"
  else
    echo "Configuring AWS access for '$AWS_ACCESS_KEY_ID' in '$AWS_REGION'"
    aws configure set aws_access_key_id $AWS_ACCESS_KEY_ID 
    aws configure set aws_secret_access_key $AWS_SECRET_ACCESS_KEY
    aws configure set default.region $AWS_REGION
    echo "AWS CLI configuration step completed."
  fi
fi

#############################################################################
# STEP 2: Create S3 bucket for deployment artifacts
# The S3 bucket will store the packaged Lambda code during deployment
#############################################################################
if [[ "$DO_CREATE_BUCKET" == "true" ]]; then
  echo "Creating S3 bucket '$BUCKET_NAME' where deployment packages will be stored"
  aws s3api create-bucket \
    --bucket $BUCKET_NAME \
    --region $AWS_REGION \
    --create-bucket-configuration LocationConstraint=$AWS_REGION
  # Note: If you get a 'BucketAlreadyOwnedByYou' error, it means the bucket already exists
  # and you can safely ignore this error

  #############################################################################
  # STEP 3: Set up lifecycle policy for S3 bucket
  # This automatically deletes old deployment packages after 24 hours
  # to prevent accumulation of unused artifacts and minimize storage costs
  #############################################################################
  echo "Setting up lifecycle policy to clean up old deployment packages after 24 hours"
  aws s3api put-bucket-lifecycle-configuration \
    --bucket $BUCKET_NAME  \
    --lifecycle-configuration '{
        "Rules": [
            {
                "Filter": {},
                "Status": "Enabled",
                "Expiration": {
                    "Days": 1
                },
                "ID": "QuickExpiration"
            }
        ]
    }'
  echo "S3 bucket creation step completed."
fi

#############################################################################
# STEP 4: Create DynamoDB table for chat data
# This table will store all chat sessions with chat_id as the primary key
#############################################################################
if [[ "$DO_CREATE_TABLE" == "true" ]]; then
  echo "Creating DynamoDB table '$TABLE_NAME' to store chat sessions"
  aws dynamodb create-table \
    --table-name $TABLE_NAME \
    --attribute-definitions AttributeName=chat_id,AttributeType=S \
    --key-schema AttributeName=chat_id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region $AWS_REGION
  echo "DynamoDB table creation step completed."
  # Notes on the DynamoDB settings:
  # - chat_id is the primary key (HASH key in DynamoDB terminology)
  # - PAY_PER_REQUEST means you only pay for actual usage (no capacity planning needed)
  # - The table will automatically scale based on traffic
  # - If you get a 'ResourceInUseException', the table already exists and you can ignore this error
fi

# Final message
if [[ "$DO_CONFIGURE_AWS" == "true" && "$DO_CREATE_BUCKET" == "true" && "$DO_CREATE_TABLE" == "true" ]]; then
  echo "All setup steps completed. You can now deploy your application using './b_deploy.sh'"
else
  echo "Selected steps completed. After you have completed all steps, you can deploy your application using './b_deploy.sh'"
fi
# backend.tf — Remote state stub. Fill in your S3 bucket + DynamoDB table
# before running `terraform init`. Kept separate so other modules can change
# without disturbing backend wiring.

terraform {
  backend "s3" {
    # bucket         = "my-tfstate-bucket"
    # key            = "meapy/terraform.tfstate"
    # region         = "eu-west-1"
    # dynamodb_table = "terraform-locks"
    # encrypt        = true
  }
}

pipeline {
    agent any

    environment {
        // Folder on the EC2 host where .env / credentials.json / token.json
        // were copied manually (see SETUP_GUIDE.md, Step 5).
        // This folder is NEVER part of the Git repo.
        SECRETS_DIR = "/opt/agent-secrets"
    }

    options {
        timestamps()
        disableConcurrentBuilds()
    }

    triggers {
        // Fires automatically when the GitHub webhook hits Jenkins
        githubPush()
    }

    stages {

        stage('Checkout code') {
            steps {
                checkout scm
            }
        }

        stage('Inject secrets') {
            steps {
                sh '''
                    cp ${SECRETS_DIR}/.env backend/.env
                    cp ${SECRETS_DIR}/credentials.json backend/credentials.json
                    cp ${SECRETS_DIR}/token.json backend/token.json
                '''
            }
        }

        stage('Build images') {
            steps {
                sh 'docker compose build'
            }
        }

        stage('Stop old containers') {
            steps {
                sh 'docker compose down || true'
            }
        }

        stage('Deploy') {
            steps {
                sh 'docker compose up -d'
            }
        }

        stage('Cleanup old images') {
            steps {
                sh 'docker image prune -f'
            }
        }
    }

    post {
        success {
            echo 'Deployment successful.'
        }
        failure {
            echo 'Deployment failed — check the stage logs above.'
        }
    }
}

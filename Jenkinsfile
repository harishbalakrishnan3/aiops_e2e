import groovy.transform.Field

def current_stage = ''

@Field
def failed_stages = ' '

pipeline {
    agent {
        label 'ecs-cdo-python-modules'
    }

    environment {
        CDO_TOKEN = ''
        HELIOS_TOKEN = ''
        ENV = 'staging'
        PYTHONUNBUFFERED = 'true'
    }

    stages {
        stage('SCM Checkout') {
            steps {
                script {
                    current_stage = 'SCM Checkout'
                    failed_stages = ' '
                }
                checkout scmGit(branches: [[name: 'main']], extensions: [], userRemoteConfigs: [[url: 'https://github.com/harishbalakrishnan3/aiops_e2e']])
            }
        }

        stage('Download Prometheus and Promtool') {
            steps {
                runStage('Download Prometheus and Promtool' , '''
                    cd utils
                    chmod 777 ./download_prometheus.sh
                    chmod 777 ./download_mimirtool.sh
                    ./download_prometheus.sh
                ''')
            }
        }

        stage('Download Mimirtool') {
            steps {
                runStage('Download Mimirtool' , '''
                    cd utils
                    ./download_mimirtool.sh
                    ls -larth
                    cd ..
                    ls -larth
                ''')
            }
        }

        stage('Install Python Dependencies') {
            steps {
                runStage('Install Python Dependencies' , 'poetry install --no-root')
            }
        }

        stage('Offboard/Onboard') {
            steps {
                catchError(buildResult: 'FAILURE', stageResult: 'FAILURE') {
                    runStage('Offboard/Onboard' , 'poetry run behave --no-capture --format plain features/000_Onboard.feature')
                }
            }
        }

        stage('Wait for 12 minutes') {
            // There can be delay upto 10minutes after onboard for the threshold ingestion to happen as the ticks come every 10 mins
            steps {
                sleep(720)
            }
        }

        stage('Run feature tests') {
            parallel {
                stage('Elephant Flows') {
                    steps {
                        runStage('Elephant Flows' , 'poetry run behave --no-capture --format plain features/100_ElephantFlows.feature')
                    }
                }

                stage('Correlation') {
                    steps {
                        runStage('Correlation' , 'poetry run behave --no-capture --format plain features/200_Correlation.feature')
                    }
                }

                stage('RA-VPN Forecasting') {
                    steps {
                        runStage('RA-VPN Forecasting' , 'poetry run behave --no-capture --format plain features/300_RAVPN.feature')
                    }
                }

                stage('Anomaly Detection') {
                    steps {
                        runStage('Anomaly Detection' , 'poetry run behave --no-capture --format plain features/400_Anomaly.feature')
                    }
                }
            }
        }
    }

    post {
        success {
            script {
                sendMessageToWebex("E2E Run #${env.BUILD_NUMBER} is successful. View the job here: ${env.BUILD_URL}")
            }
        }
        failure {
            script {
                echo "Test log Failed at stage(s) : ${failed_stages}"
                sendMessageToWebex("E2E Run #${env.BUILD_NUMBER} failed at stage(s) : ${failed_stages}. View the job here: ${env.BUILD_URL}")
            }
        }
        always {
            script {
                archiveArtifacts artifacts: '*_output.txt', allowEmptyArchive: true
            }
        }
    }
}


def runStage(stage_name, command) {
    script {
        def safeStageName = stage_name.replaceAll("[^a-zA-Z0-9_-]", "_")
        
        def logFile = "${safeStageName}_output.txt"

        try {
            // Pre-create the log file with permissions to prevent exceptions
            sh "touch ${logFile} && chmod 777 ${logFile}"

            // Execute the command, redirecting output to the log file
            // Note: The exit code is captured separately
            sh(script: """
                #!/bin/bash
                set -e
                ${command} > ${logFile} 2>&1
            """)
            
            // Read the output from the log file to display in the console
            def output = readFile(logFile).trim()
            echo "Output of '${stage_name}':\n${output}"
            
        } catch (Exception e) {
            // This block will catch failures in the sh step itself
            failed_stages = "${failed_stages} ${stage_name} ,"
            def errorMessage = "Failed during '${stage_name}' stage: ${e.getMessage()}"
            
            // Ensure we have something in the log file
            try {
                def existingOutput = readFile(logFile).trim()
                if (!existingOutput) {
                    writeFile file: logFile, text: errorMessage
                }
            } catch (Exception readEx) {
                writeFile file: logFile, text: errorMessage
            }
            
            error(errorMessage)
        }
    }
}

def sendMessageToWebex(String messageText) {
    def command = """curl -X POST -H "Content-Type: application/json" -d '{"markdown" : "${messageText}"}' https://webexapis.com/v1/webhooks/incoming/{webhook_id}"""
    sh command
}
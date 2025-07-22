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
        stage('Prepare Logs Directory') {
            steps {
                sh 'mkdir -p logs'
            }
        }

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
            // Archive all logs
            archiveArtifacts artifacts: 'logs/*.txt', allowEmptyArchive: true
        }
    }
}

def runStage(stage_name, command) {
    script {
        // Sanitize file name
        def safeStageName = stage_name.replaceAll("[^a-zA-Z0-9_-]", "_")
        def logFile = "logs/${safeStageName}_output.txt"
        
        try {
            // Use a temporary file to capture both stdout and stderr
            def tempLogFile = "${logFile}.tmp"
            
            // Run command and redirect output to temp file, then get exit status
            def exitCode = sh(script: "${command} > ${tempLogFile} 2>&1; echo \$?", returnStdout: true).trim() as Integer
            
            // Read the captured output
            def output = readFile(tempLogFile).trim()
            
            // Clean up temp file
            sh "rm -f ${tempLogFile}"
            
            if (exitCode == 0) {
                // Success case
                writeFile file: logFile, text: output
                echo "Output of '${stage_name}':\n${output}"
            } else {
                // Failure case - still write the output to log file
                writeFile file: logFile, text: output
                echo "Output of '${stage_name}' (failed with exit code ${exitCode}):\n${output}"
                
                // Track failed stage
                failed_stages = "${failed_stages} ${stage_name} ,"
                
                // Throw error to mark stage as failed
                error("Stage '${stage_name}' failed with exit code ${exitCode}")
            }
        } catch (Exception e) {
            // Fallback error handling
            echo "Exception during '${stage_name}' stage: ${e.getMessage()}"
            failed_stages = "${failed_stages} ${stage_name} ,"
            
            def errorLog = "Exception occurred: ${e.getMessage()}"
            writeFile file: logFile, text: errorLog
            
            error("Failed during '${stage_name}' stage: ${e.getMessage()}")
        }
    }
}

def sendMessageToWebex(String messageText) {
    def command = """curl -X POST -H "Content-Type: application/json" -d '{"markdown" : "${messageText}"}' https://webexapis.com/v1/webhooks/incoming/{webhook_id}"""
    sh command
}

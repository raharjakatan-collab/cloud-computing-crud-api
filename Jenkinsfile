pipeline {
    agent any

    parameters {
        string(
            name: 'ROLLBACK_TO',
            defaultValue: '',
            description: 'Kosongkan untuk build normal. Isi tag image lama (nomor build atau commit SHA) untuk rollback manual.'
        )
    }

    environment {
        PYTHONUNBUFFERED = '1'
        REGISTRY_NAME = 'python-crud-api'
        CONTAINER_NAME = 'production-api-container'
        PORT_MAPPING = '5000:5000'
        VOLUME_NAME = 'production-api-data'
        NETWORK_NAME = 'jenkins-net'
    }

    stages {
        stage('1. Checkout Code') {
            steps {
                echo 'Checking out source code from GitHub'
                checkout scm
                script {
                    env.GIT_SHORT_SHA = sh(
                        script: 'git rev-parse --short=7 HEAD',
                        returnStdout: true
                    ).trim()
                    env.DEPLOY_TAG = params.ROLLBACK_TO ? params.ROLLBACK_TO.trim() : env.GIT_SHORT_SHA
                    env.DEPLOYED = 'false'
                }
                echo "Commit ${env.GIT_SHORT_SHA}, tag yang akan dideploy: ${env.DEPLOY_TAG}"
            }
        }

        stage('2. Code Syntax Verification') {
            when { expression { !params.ROLLBACK_TO } }
            steps {
                sh 'python3 -m py_compile app.py'
            }
        }

        stage('3. Automated Tests') {
            when { expression { !params.ROLLBACK_TO } }
            steps {
                sh 'python3 -m unittest discover -s tests -v'
            }
        }

        stage('4. Build Docker Image') {
            when { expression { !params.ROLLBACK_TO } }
            steps {
                sh 'docker build -t ${REGISTRY_NAME}:${BUILD_NUMBER} -t ${REGISTRY_NAME}:${GIT_SHORT_SHA} -t ${REGISTRY_NAME}:latest .'
            }
        }

        stage('5. Automated Deployment') {
            steps {
                // Tag yang tidak ada harus gagal sebelum container lama disentuh.
                sh 'docker image inspect ${REGISTRY_NAME}:${DEPLOY_TAG} --format "Image ${REGISTRY_NAME}:${DEPLOY_TAG} = {{.Id}}"'
                script { env.DEPLOYED = 'true' }
                sh '''
                    if docker inspect ${CONTAINER_NAME} >/dev/null 2>&1; then
                        PREVIOUS_IMAGE=$(docker inspect --format '{{.Image}}' ${CONTAINER_NAME})
                        docker tag ${PREVIOUS_IMAGE} ${REGISTRY_NAME}:previous
                        echo "Image sebelumnya disimpan sebagai ${REGISTRY_NAME}:previous"
                    fi
                    docker stop ${CONTAINER_NAME} || true
                    docker rm ${CONTAINER_NAME} || true
                    docker volume create ${VOLUME_NAME}
                    docker run -d \
                        --name ${CONTAINER_NAME} \
                        --network ${NETWORK_NAME} \
                        -p ${PORT_MAPPING} \
                        -v ${VOLUME_NAME}:/var/lib/backend_data \
                        ${REGISTRY_NAME}:${DEPLOY_TAG}
                '''
            }
        }

        // localhost di sini berarti container Jenkins, jadi API dipanggil
        // lewat nama container pada network yang sama.
        stage('6. Health Check') {
            steps {
                sh '''
                    for attempt in 1 2 3 4 5 6 7 8 9 10; do
                        if curl -fsS http://${CONTAINER_NAME}:5000/health; then
                            echo
                            docker logs --tail 20 ${CONTAINER_NAME}
                            exit 0
                        fi
                        echo "Menunggu API siap (percobaan ${attempt}/10)"
                        sleep 2
                    done
                    docker logs --tail 20 ${CONTAINER_NAME}
                    exit 1
                '''
            }
        }
    }

    post {
        success {
            echo "Pipeline completed successfully. Berjalan: ${env.REGISTRY_NAME}:${env.DEPLOY_TAG}"
        }
        failure {
            script {
                if (env.DEPLOYED == 'true') {
                    echo 'Pipeline gagal setelah deploy. Rollback otomatis ke image sebelumnya.'
                    sh '''
                        if ! docker image inspect ${REGISTRY_NAME}:previous >/dev/null 2>&1; then
                            echo "Tidak ada image sebelumnya, rollback dilewati"
                            exit 0
                        fi
                        docker rm -f ${CONTAINER_NAME} || true
                        docker run -d \
                            --name ${CONTAINER_NAME} \
                            --network ${NETWORK_NAME} \
                            -p ${PORT_MAPPING} \
                            -v ${VOLUME_NAME}:/var/lib/backend_data \
                            ${REGISTRY_NAME}:previous
                        for attempt in 1 2 3 4 5 6 7 8 9 10; do
                            if curl -fsS http://${CONTAINER_NAME}:5000/health; then
                                echo
                                echo "ROLLBACK BERHASIL: layanan kembali ke ${REGISTRY_NAME}:previous"
                                exit 0
                            fi
                            sleep 2
                        done
                        echo "ROLLBACK GAGAL: periksa manual"
                        exit 1
                    '''
                } else {
                    echo 'Pipeline gagal sebelum deploy. Container produksi tidak disentuh.'
                }
            }
        }
    }
}

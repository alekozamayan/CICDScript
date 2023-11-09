
// Changelog pattern match control method 
boolean matchChangelog(GString ptrnString)
{
    def ptrn = ~"${ptrnString}"
    
    for(i in currentBuild.changeSets)
    {
        for(j in i.items)
        {
            if(j.msg =~ ptrn)
            {
                echo "Changelog match detected: ${ptrnString}"
                return true
            }
        }
    }
    
    return false
}

// Changelog data collect method
String getChangeLogString()
{
    def logstring = " "
    
    for (i in currentBuild.changeSets)
    {
        for (j in i.items)
        {
            logstring += "\n${j.commitId} by ${j.author} on ${new Date(j.timestamp)}:\n\n"
            logstring += "${j.msg}\n\n"
                        
            def files = new ArrayList(j.affectedFiles)
            for (k in files) {
                logstring += "${k.editType.name} ${k.path}\n"                
            }
            
            logstring += "\n------------------------------------------------------------\n"
        }
    }

    return logstring
}



pipeline {    
    agent any
    environment {
        //Changelog regex trigs
        CLOG_NOBUILD    = '\\[ci NOBUILD\\]'
        CLOG_NODEPLOY   = '\\[ci NODEPLOY\\]'
        
    }
    
    parameters {
        booleanParam(name: 'NOBUILD',  defaultValue: false, description: 'If true, do not build.')
        booleanParam(name: 'NODEPLOY', defaultValue: false, description: 'If true, do not deploy.')
        credentials(name: 'vcscreds', description:'A user to build with', defaultValue: 'Enter the ID value of Jenkins Credential you use to access VCS here.', credentialType: "Username with password", required: false)
        string(name: 'emailRecipientList', defaultValue: 'alice.cooper@gmail.com, bob.marley@hotmail.com', description: 'Email recipient list.')       
        text(name: 'additionalLogText', defaultValue: ' ', description: 'If you want to write additional entry to commit log of the artifact, enter here.')
    }
    
    triggers {pollSCM('H/2 * * * *')}
    
    stages {
        stage('Main') {
            // Pipeline must work unless NOBUILD command is given
            when {
                expression {return ( params.NOBUILD == false ) && ( matchChangelog("${env.CLOG_NOBUILD}") == false ) }
            }

            stages {
                stage('Build') {                                        
                    steps {
                        emailext body: '''$PROJECT_NAME - Build # $BUILD_NUMBER :

Build cause : ${BUILD_CAUSE}

Changes since last build:
${CHANGES_SINCE_LAST_BUILD}

Additional logs:
''' + "${params.additionalLogText}" + '''

Check console output at $RUN_DISPLAY_URL to view the progress.''', subject: '$PROJECT_NAME - Build # $BUILD_NUMBER Started To Build', to: "${params.emailRecipientList}"
                        // Run build script with credentials, pass changelog file                    
                        withCredentials([usernamePassword(credentialsId: 'vcscreds', passwordVariable: 'VCS_PASS', usernameVariable: 'VCS_USR')]) {
                            bat 'python CICDScript.py -v -c build CICDConfig.xml --username %VCS_USR% --passwd %VCS_PASS%'
                        }                
                    }
                }
                
                // Deploy stage must work unless NODEPLOY command is given
                stage('Deploy') {
                    when {                        
                        expression { return ( params.NODEPLOY == false ) && ( matchChangelog("${env.CLOG_NODEPLOY}") == false ) }
                    }
                    
                    steps {
                        script {                    
                            def logfilename = 'logfile.txt'
                            def deploypathfilename = 'deployurl.txt'
                            // Get changelog data and write it to a temporary file
                            writeFile file: logfilename, text: "${params.additionalLogText}" + getChangeLogString()
                            
                            // Run deploy script with credentials, pass changelog file
                            withCredentials([usernamePassword(credentialsId: 'vcscreds', passwordVariable: 'VCS_PASS', usernameVariable: 'VCS_USR')]) {
                                bat "python CICDScript.py -v -c deploy CICDConfig.xml -F ${logfilename} --deploypathfile ${deploypathfilename} --username %VCS_USR% --passwd %VCS_PASS%"
                            }
                            
                            String deploypathtext = readFile "${deploypathfilename}"
                            
                            emailext attachLog: true, body: '''$PROJECT_NAME - Build # $BUILD_NUMBER :

Deployed to:
''' + "${deploypathtext}" + '''

Check $RUN_DISPLAY_URL to view the progress and artifacts.''', subject: '$PROJECT_NAME - Build # $BUILD_NUMBER Successful!', to: "${params.emailRecipientList}"
                        
                        } 
                    }
                }
            }
        }   
    }

    post {
        always {
            script {
                if ( currentBuild.currentResult == "ABORTED" || currentBuild.currentResult == "FAILURE" )
                {
                    emailext attachLog: true, body: '''$PROJECT_NAME - Build # $BUILD_NUMBER :
Failed to complete build. You can check build log in the attachment.

Check console output at $RUN_DISPLAY_URL to view the progress.''', subject: '$PROJECT_NAME - Build # $BUILD_NUMBER $BUILD_STATUS!', to: "${params.emailRecipientList}"
                }
            }
        }
        cleanup{
            // Clean up workspace
            cleanWs()
        }
    }
}

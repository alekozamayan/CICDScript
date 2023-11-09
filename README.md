### CICDScript (A Simple General Purpose Script to Build a CI/CD Pipeline)

This is a Python script project, aims to help people to setup an automated build/deploy
environment as simple to be used by many people which are not acquinted to CI tools. The
purposes of this project are:

- To abstract various CI/CD tools and their configurations
- To abstract CI/CD tool configuration interface from the developers as much as possible,
to make them to setup their own build/deploy flow only with a simple familiar (.xml)
interface.
- To help to create a common way of a simple CI/CD workflow used in small projects/groups,
especially working in a closed environment, much more simple.

It is designed to work with a single Version Control System (for now only SVN supported).
It can do any file transactions using VCS and filesystem in every direction.

The 2 CI steps (build and deploy) are defined in an .xml configuration file (CICDConfig.xml)
which is processed by the script. "CICDConfig.xml" example file has commentary lines
explaining every node and their parameters.

"CICDScript.py" help documentation can be reached by command line :
`python CICDScript.py --help`

To integrate with Jenkins CI, there is a Jenkins declarative pipeline script (Jenkinsfile)
provided in the project. It is aimed that Jenkinsfile should not be changed once configured
according to the needs, which are:

- vcscreds              : Jenkins Credentials ID used to access VCS
- emailRecipientList    : mail notification recipient list.

There is a Test directory provided, containing an example SVN repository with a CI environment
inside. It can be tested using Jenkins (see Test/README.md)

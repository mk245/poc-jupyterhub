FROM myproject/minimal-notebook:latest

USER root

# Required for ffmpeg.

RUN yum install -y https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm --skip-broken && \
    yum-config-manager -y --add-repo https://negativo17.org/repos/epel-multimedia.repo --skip-broken && \
    yum install --enablerepo=epel -y ffmpeg --skip-broken && \
    yum -y clean all --enablerepo='*' --skip-broken

USER 1001

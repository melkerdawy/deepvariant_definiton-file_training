Bootstrap: localimage
From: deepvariant-0.7.0.simg

# Modified from: https://gist.github.com/pansapiens/717efcdefb51fa0ce1a6abf092bcb2f4
# Install Google Cloud SDK for the gcloud tool, then:
# We grab the official Docker image, push it to a locally running container repo, then get
# Singularity to pull it back.
# docker pull gcr.io/deepvariant-docker/deepvariant:0.7.0
# docker tag gcr.io/deepvariant-docker/deepvariant:0.7.0 localhost:5000/deepvariant:0.7.0
# docker run -d -p 5000:5000 --restart=always --name registry registry:2
# docker push localhost:5000/deepvariant:0.7.0
# sudo SINGULARITY_NOHTTPS=1 singularity pull docker://localhost:5000/deepvariant:0.7.0
#
# Then use that container image to make this customized one
# sudo singularity build deepvariant-custom.simg Singularity_training.spec

%environment
    PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
    DV_GPU_BUILD=0
    export PATH DV_GPU_BUILD

%apprun make_examples_training
    exec /opt/deepvariant/bin/make_examples \
    --mode training \
    --ref /dv2/input/reference.fasta.gz \
    --reads /dv2/input/reads.bam \
    --examples training_set.with_label.tfrecord.gz \
    --truth_variants /dv2/input/truthdata.vcf.gz \
    --confident_regions /dv2/input/thruthdata.bed \
    --sample_name "train" \
    --exclude_regions "chr20 chr21 chr22" 

%apprun make_examples_val
    exec /opt/deepvariant/bin/make_examples \
    --mode training \
    --ref dv2/input/reference.fasta.gz \
    --reads dv2/input/reads.bam \
    --examples validation_set.with_label.tfrecord.gz \
    --truth_variants /dv2/input/truthdata.vcf.gz \ 
    --confident_regions /dv2/input/thruthdata.bed \
    --sample_name "validate" \
    --regions "chr20 chr21" 

%apprun make_examples_test
    exec /opt/deepvariant/bin/make_examples \
    --mode calling \
    --ref dv2/input/reference.fasta.gz \
    --reads dv2/input/reads.bam \
    --examples test_set.no_label.tfrecord.gz \
    --sample_name "test" \
    --regions "chr20" 

%runscript
if [ $# -eq 0 ]; then
    echo '''Example Usage:

    sudo singularity run --bind input:/dv2/input/ --app make_examples_training deepvariant-custom.simg 

    singularity run --bind input:/dv2/input/ --app make_examples_val deepvariant-custom.simg

    singularity run --bind input:/dv2/input/ --app make_examples_test deepvariant-custom.simg
    
else
    exec "$@"
fi


%post
    export CLOUD_SDK_REPO="cloud-sdk-$(lsb_release -c -s)"
    echo "deb http://packages.cloud.google.com/apt $CLOUD_SDK_REPO main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
    curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add -
    apt-get -y update && apt-get install -y google-cloud-sdk parallel wget
    rm -rf /var/lib/apt/lists/*

    # https://github.com/google/deepvariant/blob/r0.5/deepvariant/docker/Dockerfile
    BASH_HEADER='#!/bin/bash' && \
    printf "%s\n%s\n" \
        "${BASH_HEADER}" \
        'python /opt/deepvariant/bin/make_examples.zip "$@"' > \
        /opt/deepvariant/bin/make_examples && \
    printf "%s\n%s\n" \
        "${BASH_HEADER}" \
        'python /opt/deepvariant/bin/call_variants.zip "$@"' > \
        /opt/deepvariant/bin/call_variants && \
    printf "%s\n%s\n" \
        "${BASH_HEADER}" \
        'python /opt/deepvariant/bin/postprocess_variants.zip "$@"' > \
        /opt/deepvariant/bin/postprocess_variants && \
    printf "%s\n%s\n" \
        "${BASH_HEADER}" \
        'python /opt/deepvariant/bin/model_train.zip "$@"' > \
        /opt/deepvariant/bin/model_train && \
    printf "%s\n%s\n" \
        "${BASH_HEADER}" \
        'python /opt/deepvariant/bin/model_eval.zip "$@"' > \
        /opt/deepvariant/bin/model_eval && \
    chmod +x /opt/deepvariant/bin/make_examples \
             /opt/deepvariant/bin/call_variants \
             /opt/deepvariant/bin/postprocess_variants \
             /opt/deepvariant/bin/model_train \
             /opt/deepvariant/bin/model_eval

     mkdir -p /models/wgs
     mkdir -p /models/wes
     BIN_VERSION="0.7.0"
     MODEL_VERSION=$BIN_VERSION
     BUCKET="gs://deepvariant"
     MODEL_NAME_WGS="DeepVariant-inception_v3-${MODEL_VERSION}+data-wgs_standard"
     MODEL_NAME_WES="DeepVariant-inception_v3-${MODEL_VERSION}+data-wes_standard"
     MODEL_BUCKET_WGS="${BUCKET}/models/DeepVariant/${MODEL_VERSION}/${MODEL_NAME_WGS}/*"
     MODEL_BUCKET_WES="${BUCKET}/models/DeepVariant/${MODEL_VERSION}/${MODEL_NAME_WES}/*"
     gsutil cp -R "${MODEL_BUCKET_WGS}" /models/wgs/
     gsutil cp -R "${MODEL_BUCKET_WES}" /models/wes/

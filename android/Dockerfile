# syntax=docker/dockerfile:1
FROM ghcr.io/cirruslabs/android-sdk:34
ARG GRADLE_VERSION=8.6

# Use JDK 21 inside the base image (available in base image)
ENV JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64
ENV PATH="$JAVA_HOME/bin:$PATH"

# Consistent SDK env
ENV ANDROID_HOME=/opt/android-sdk
ENV ANDROID_SDK_ROOT=/opt/android-sdk

# Gradle home inside project to cache in mounted volume
ENV GRADLE_USER_HOME=/workspace/.gradle

# Install utilities and Gradle distribution
RUN apt-get update \
	&& apt-get install -y curl unzip \
	&& rm -rf /var/lib/apt/lists/* \
	&& curl -sL https://services.gradle.org/distributions/gradle-${GRADLE_VERSION}-bin.zip -o /tmp/gradle.zip \
	&& unzip -d /opt/gradle /tmp/gradle.zip \
	&& rm /tmp/gradle.zip
ENV GRADLE_HOME=/opt/gradle/gradle-${GRADLE_VERSION}
ENV PATH="$GRADLE_HOME/bin:$PATH"

# Install required SDK packages (idempotent)
RUN sdkmanager --version \
	&& yes | sdkmanager --licenses >/dev/null || true \
	&& sdkmanager "platform-tools" "platforms;android-34" "build-tools;34.0.0" >/dev/null || true

WORKDIR /workspace

# Copy settings and top-level build files
COPY settings.gradle settings.gradle
COPY build.gradle build.gradle

# Copy app sources
COPY app app

# Default command builds debug APK using installed Gradle
CMD ["gradle", "--no-daemon", "assembleDebug"]

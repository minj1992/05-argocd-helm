#!/bin/bash

# Check if tag is provided
if [ -z "$1" ]; then
    echo "Error: No tag provided."
    echo "Usage: ./rebuild_and_deploy.sh <tag>"
    exit 1
fi

TAG=$1
DOCKER_USER="minjteck"
SERVICES=("audit" "forgot-password" "frontend" "login" "logout" "profile" "register")

echo "🚀 Starting rebuild and deploy process with tag: $TAG"

for SVC in "${SERVICES[@]}"; do
    IMAGE="${DOCKER_USER}/${SVC}-service"
    
    echo ""
    echo "------------------------------------------"
    echo "📦 Processing Service: $SVC"
    echo "------------------------------------------"
    
    # 1. Cleanup existing local images for this service
    echo "🧹 Cleaning up local images for $IMAGE..."
    docker rmi $(docker images -q "$IMAGE") --force 2>/dev/null
    
    # 2. Build new image
    echo "🏗️  Building $IMAGE:$TAG..."
    cp mq_helper.py "apps/$SVC/app/mq_helper.py"
    docker build -t "$IMAGE:$TAG" "apps/$SVC/app"
    
    if [ $? -ne 0 ]; then
        echo "❌ Error building $SVC. Skipping..."
        continue
    fi
    
    # 3. Push to registry
    echo "⬆️  Pushing $IMAGE:$TAG..."
    docker push "$IMAGE:$TAG"
    
    # 4. Update Helm Values
    VALUES_FILE="argocd/manifests/$SVC/values.yaml"
    if [ -f "$VALUES_FILE" ]; then
        echo "📝 Updating Helm values: $VALUES_FILE"
        # Update the tag line in values.yaml
        sed -i "s|tag: \".*\"|tag: \"${TAG}\"|g" "$VALUES_FILE"
    else
        echo "⚠️  Warning: Values file $VALUES_FILE not found."
    fi
done

echo ""
echo "------------------------------------------"
echo "✅ All services built, pushed, and Helm values updated to tag: $TAG"
echo "# ArgoCD will detect the changes in values.yaml and sync automatically."
echo "# To apply root changes manually, run:"
echo "# kubectl apply -f root-argocd.yaml"

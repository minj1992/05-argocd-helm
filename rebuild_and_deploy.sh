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
    
    # 4. Update Manifest
    MANIFEST="argocd/manifests/$SVC/deployment.yaml"
    if [ -f "$MANIFEST" ]; then
        echo "📝 Updating manifest: $MANIFEST"
        # Update the image line with the new tag
        sed -i "s|image: ${IMAGE}:.*|image: ${IMAGE}:${TAG}|g" "$MANIFEST"
    else
        echo "⚠️  Warning: Manifest $MANIFEST not found."
    fi
done

echo ""
echo "------------------------------------------"
echo "✅ All services built, pushed, and manifests updated to tag: $TAG"
echo "# To apply changes manually, run:"
echo "# kubectl apply -f argocd/manifests/frontend/rbac.yaml"
echo "# kubectl apply -f root-argocd.yaml"

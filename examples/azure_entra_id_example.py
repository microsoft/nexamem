"""
Example: Using NexaMem with Microsoft Entra ID Authentication for Azure Redis Cache

This example demonstrates how to use Microsoft Entra ID (formerly Azure AD) 
authentication with Azure Redis Cache instead of access keys.

Prerequisites:
1. Azure Redis Cache with Entra ID authentication enabled
2. Azure identity configured (Service Principal, Managed Identity, or user)
3. Appropriate Redis Data Contributor role assigned
"""
from nexamem import initialize, ChatHistory

def main():
    print("🔐 NexaMem with Microsoft Entra ID Authentication")
    print("=" * 55)
    
    # Microsoft Entra ID authentication configuration
    entra_config = {
        "history_storage": "redis",
        "redis_host": "your-cache.redis.cache.windows.net",  # Replace with your cache
        "redis_port": 6380,
        "redis_ssl": True,
        "redis_auth_method": "entra_id",  # Use Entra ID instead of access key
        "redis_entra_scope": "https://redis.azure.com/.default",  # Default scope
        "redis_key_prefix": "myapp_entra:",
        "debug": True
    }
    
    # Alternative configurations for different Azure identity types:
    
    # 1. For Azure App Service/Function with Managed Identity:
    # entra_config = {
    #     "history_storage": "redis",
    #     "redis_host": "your-cache.redis.cache.windows.net",
    #     "redis_auth_method": "entra_id",
    #     "redis_ssl": True
    # }
    
    # 2. For development with Azure CLI login:
    # Make sure you've run: az login
    # The DefaultAzureCredential will use your CLI credentials
    
    # 3. For service principal authentication, set these environment variables:
    # AZURE_CLIENT_ID=your-client-id
    # AZURE_CLIENT_SECRET=your-client-secret  
    # AZURE_TENANT_ID=your-tenant-id
    
    try:
        print("🔧 Initializing with Microsoft Entra ID authentication...")
        initialize(entra_config)
        print("✅ Successfully authenticated with Entra ID!")
        
        # Create ChatHistory instance
        print("\n💾 Creating ChatHistory instance...")
        history = ChatHistory()
        
        print("\n📝 Testing Redis operations with Entra ID...")
        
        # Add messages
        messages = [
            ("user", "Hello! I'm using Entra ID authentication."),
            ("assistant", "Great! Microsoft Entra ID provides better security than access keys."),
            ("user", "What are the main benefits?"),
            ("assistant", "Benefits include: no shared secrets, centralized identity management, RBAC, and audit logging."),
            ("user", "How does token refresh work?"),
            ("assistant", "NexaMem automatically handles token refresh using azure-identity library.")
        ]
        
        for role, content in messages:
            history.add_message(role, content)
            print(f"   ✅ Added [{role}]: {content[:50]}...")
        
        print(f"\n📊 Total messages stored: {len(history.get_history())}")
        
        # Demonstrate query functionality
        print("\n🔍 Searching for messages about 'Entra'...")
        entra_messages = history.query_redis(pattern="Entra")
        for msg in entra_messages:
            print(f"   🔎 [{msg['role']}]: {msg['content'][:60]}...")
        
        # Show Redis connection info
        print("\n📈 Redis Connection Info:")
        try:
            info = history.get_redis_info()
            for key, value in info.items():
                if key != 'error':
                    print(f"   {key}: {value}")
        except Exception as e:
            print(f"   Could not retrieve info: {e}")
        
        print("\n✅ Entra ID authentication working successfully!")
        print("🔄 Token refresh is handled automatically")
        
        # Clean up
        print("\n🧹 Clearing test data...")
        history.clear()
        print("   Done!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n💡 To use Microsoft Entra ID authentication:")
        print("   1. Enable Entra ID authentication on your Azure Redis Cache")
        print("   2. Assign 'Redis Data Contributor' role to your identity")
        print("   3. Ensure azure-identity package is installed: pip install azure-identity")
        print("   4. Set up your Azure credentials:")
        print("      - For local dev: az login")
        print("      - For App Service: Enable Managed Identity")
        print("      - For Service Principal: Set AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID")

def show_authentication_methods():
    """Show different ways to authenticate with Azure"""
    print("\n🔑 Entra ID Authentication Methods:")
    print("=" * 40)
    
    print("\n1. 🏢 Managed Identity (Recommended for Azure services)")
    print("   - Enable on App Service, VM, Function App, etc.")
    print("   - No credentials in code")
    print("   - Automatic token management")
    
    print("\n2. 👤 Azure CLI (Development)")
    print("   - Run: az login")
    print("   - Uses your user credentials")
    print("   - Good for local development")
    
    print("\n3. 🤖 Service Principal (CI/CD, automation)")
    print("   - Set environment variables:")
    print("     AZURE_CLIENT_ID=your-app-id")
    print("     AZURE_CLIENT_SECRET=your-secret")
    print("     AZURE_TENANT_ID=your-tenant-id")
    
    print("\n4. 📖 Workload Identity (Kubernetes)")
    print("   - For applications running in AKS")
    print("   - Federated identity without secrets")

if __name__ == "__main__":
    main()
    show_authentication_methods()

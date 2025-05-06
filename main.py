import asyncio
import argparse
import sys
from dataclasses import dataclass   

from evo.discovery import DiscoveryAPIClient, Organization
from evo.oauth import AuthorizationCodeAuthorizer, OIDCConnector, OAuthScopes
from evo.aio import AioTransport
from evo.common import APIConnector, Environment
from evo.workspaces import WorkspaceAPIClient, Workspace
from evo.files import FileAPIClient
from evo.files.data import FileMetadata
from evo.objects import ObjectAPIClient, ObjectMetadata

from tabulate import tabulate

@dataclass
class AuthData:
    transport: AioTransport
    authorizer: AuthorizationCodeAuthorizer

def create_page_size_args(limit = 50, page = None):
    offset = 0
    if page is not None:
        offset = page.offset + page.len
    return {"limit": limit, "offset": offset}

async def paginate(api_func, limit=50, **kwargs):
    """
    Generic async generator for paginating API calls that use offset/limit pagination.
    
    Args:
        api_func: The API function to call that returns a Page object
        limit: Number of items to request per page
        **kwargs: Additional arguments to pass to the API function
    
    Yields:
        Entire pages of items from each API call
    """
    offset = 0
    total = None
    
    while total is None or offset < total:
        page_args = {"limit": limit, "offset": offset}
        # Merge with any additional kwargs
        page_args.update(kwargs)
        
        page = await api_func(**page_args)
        
        if total is None:
            total = page.total
        
        items = page.items()
        if not items:
            break
            
        yield items
        offset += len(items)

async def login(client_id: str) -> AuthData:
    REDIRECT_URL = "http://localhost:3000/signin-oidc"
    ISSUER_URL = "https://ims.bentley.com"
    USER_AGENT = "EvoPythonSDK"

    transport = AioTransport(user_agent=USER_AGENT)
    connector = OIDCConnector(transport, oidc_issuer=ISSUER_URL, client_id=client_id)
    scopes = OAuthScopes.evo_discovery | OAuthScopes.email | OAuthScopes.openid | OAuthScopes.evo_object | OAuthScopes.evo_file | OAuthScopes.evo_workspace | OAuthScopes.offline_access

    authorizer = AuthorizationCodeAuthorizer(
        redirect_url=REDIRECT_URL,
        oidc_connector=connector,
        scopes=scopes,
    )
    await authorizer.login()

    return AuthData(transport, authorizer)      


async def get_organizations(auth_data: AuthData) -> list[Organization]:
    async with APIConnector("https://discover.api.seequent.com", auth_data.transport, auth_data.authorizer) as idp_connector:
        discovery_client = DiscoveryAPIClient(idp_connector)
        organizations: list[Organization] = await discovery_client.list_organizations()
        return organizations

async def get_workspace_page(auth_data: AuthData, org_id: str, hub_url: str) -> list[Workspace]:
    hub_connector = APIConnector(hub_url, auth_data.transport, auth_data.authorizer)
    workspace_client = WorkspaceAPIClient(connector=hub_connector, org_id=org_id)

    workspaces = []
    async for page_items in paginate(workspace_client.list_workspaces, limit=50):
        workspaces.extend(page_items)
    
    return workspaces

async def get_files(auth_data: AuthData, environment: Environment) -> list[FileMetadata]:
    connector = APIConnector(environment.hub_url, auth_data.transport, auth_data.authorizer)
    file_client = FileAPIClient(environment=environment, connector=connector)
    
    files = []
    async for page_items in paginate(file_client.list_files):
        files.extend(page_items)
    
    return files

async def get_objects(auth_data: AuthData, environment: Environment) -> list[ObjectMetadata]:
    connector = APIConnector(environment.hub_url, auth_data.transport, auth_data.authorizer)
    object_client = ObjectAPIClient(environment=environment, connector=connector)
    
    objects = []
    async for page_items in paginate(object_client.list_objects):
        objects.extend(page_items)
    
    return objects

def print_objects(objects: list[ObjectMetadata]):
    objects_list = [[obj.id, obj.name] for obj in objects]
    print(tabulate(objects_list, headers=["Id", "Name"]))

def print_files(files: list[FileMetadata]):
    files_list = [[file.id, file.name, file.description] for file in files]
    print(tabulate(files_list, headers=["Id", "Name", "Description"]))

def print_workspaces(workspaces: list[Workspace]):
    workspaces_list = [[workspace.id, workspace.display_name, workspace.description] for workspace in workspaces]
    print(tabulate(workspaces_list, headers=["Id", "Name", "Description"]))

def print_organizations(organizations: list[Organization]):       
    for org in organizations:
        print(f"{org.display_name}: {org.id}")
        print("=" * 50)

        print(tabulate(org.hubs, headers=["Url", "Code", "Name", "Services"]))                
        print()


async def main():
    parser = argparse.ArgumentParser(description="Seequent Evo console explorer")

    # Create mutually exclusive group for different modes
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument("--instances", action="store_true", help="Show EVO instances for each organization")
    mode_group.add_argument("--workspaces", action="store_true", 
                        help="Show workspaces for a specific organization (requires --org-id and --instance-url)")
    mode_group.add_argument("--files", action="store_true", help="Show files for a specific workspace (requires --workspace-id and --instance-url -o)")
    mode_group.add_argument("--objects", action="store_true", help="Show objects for a specific workspace (requires --workspace-id and --instance-url -o)")

    parser.add_argument("--org-id", help="Organization ID (required with --workspaces)")
    parser.add_argument("--instance-url", help="Instance URL (required with --workspaces)")
    parser.add_argument("--workspace-id", help="Workspace ID (required with --files)")
    parser.add_argument("--client-id", required=True, help="OAuth client ID (required)")

    args = parser.parse_args()
    
    # Validate arguments
    if args.workspaces and (not args.org_id or not args.instance_url):
        parser.error("--workspaces requires both --org-id and --instance-url")

    if args.files and (not args.workspace_id or not args.instance_url or not args.org_id):
        parser.error("--files requires both --workspace-id, --instance-url and --org-id")

    if args.objects and (not args.workspace_id or not args.instance_url or not args.org_id):
        parser.error("--objects requires both --workspace-id, --instance-url and --org-id")

    if args.instances:
        auth_data = await login(args.client_id)
        organizations = await get_organizations(auth_data)
        print_organizations(organizations)

    if args.workspaces:
        auth_data = await login(args.client_id)
        workspaces = await get_workspace_page(auth_data, args.org_id, args.instance_url)
        print_workspaces(workspaces)

    if args.files:
        auth_data = await login(args.client_id)
        environment = Environment(hub_url=args.instance_url, org_id=args.org_id, workspace_id=args.workspace_id)
        files = await get_files(auth_data, environment)
        print_files(files)

    if args.objects:
        auth_data = await login(args.client_id)
        environment = Environment(hub_url=args.instance_url, org_id=args.org_id, workspace_id=args.workspace_id)
        objects = await get_objects(auth_data, environment)
        print_objects(objects)

    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
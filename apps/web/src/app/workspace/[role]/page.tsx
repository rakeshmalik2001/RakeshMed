import { WorkspaceRoleDashboardClient } from "@/components/workspace-role-dashboard-client";

type WorkspaceRoleDashboardPageProps = {
  params: Promise<{
    role: string;
  }>;
};

export default async function WorkspaceRoleDashboardPage({ params }: WorkspaceRoleDashboardPageProps) {
  const resolvedParams = await params;
  return <WorkspaceRoleDashboardClient roleParam={resolvedParams.role} />;
}

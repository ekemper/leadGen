import PageBreadcrumb from "../../components/common/PageBreadCrumb";
import ComponentCard from "../../components/common/ComponentCard";
import Avatar from "../../components/ui/avatar/Avatar";
import PageMeta from "../../components/common/PageMeta";

export default function Avatars() {
  return (
    <>
      <PageMeta
        title="React.js Avatars Dashboard | TailAdmin - React.js Admin Dashboard Template"
        description="This is React.js Avatars Dashboard page for TailAdmin - React.js Tailwind CSS Admin Dashboard Template"
      />
      <PageBreadcrumb pageTitle="Avatars" />
      <div className="space-y-5 sm:space-y-6">
        <ComponentCard title="Default Avatar">
          <div className="flex flex-wrap items-center gap-4">
            <Avatar icon={true} size="xsmall" />
            <Avatar icon={true} size="small" />
            <Avatar icon={true} size="medium" />
            <Avatar icon={true} size="large" />
            <Avatar icon={true} size="xlarge" />
            <Avatar icon={true} size="xxlarge" />
          </div>
        </ComponentCard>
        <ComponentCard title="Avatar with online indicator">
          <div className="flex flex-wrap items-center gap-4">
            <Avatar icon={true} size="xsmall" status="online" />
            <Avatar icon={true} size="small" status="online" />
            <Avatar icon={true} size="medium" status="online" />
            <Avatar icon={true} size="large" status="online" />
            <Avatar icon={true} size="xlarge" status="online" />
            <Avatar icon={true} size="xxlarge" status="online" />
          </div>
        </ComponentCard>
        <ComponentCard title="Avatar with Offline indicator">
          <div className="flex flex-wrap items-center gap-4">
            <Avatar icon={true} size="xsmall" status="offline" />
            <Avatar icon={true} size="small" status="offline" />
            <Avatar icon={true} size="medium" status="offline" />
            <Avatar icon={true} size="large" status="offline" />
            <Avatar icon={true} size="xlarge" status="offline" />
            <Avatar icon={true} size="xxlarge" status="offline" />
          </div>
        </ComponentCard>
        <ComponentCard title="Avatar with busy indicator">
          <div className="flex flex-wrap items-center gap-4">
            <Avatar icon={true} size="xsmall" status="busy" />
            <Avatar icon={true} size="small" status="busy" />
            <Avatar icon={true} size="medium" status="busy" />
            <Avatar icon={true} size="large" status="busy" />
            <Avatar icon={true} size="xlarge" status="busy" />
            <Avatar icon={true} size="xxlarge" status="busy" />
          </div>
        </ComponentCard>
      </div>
    </>
  );
}

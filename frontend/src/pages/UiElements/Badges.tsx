import PageBreadcrumb from "../../components/common/PageBreadCrumb";
import Badge from "../../components/ui/badge/Badge";
import PageMeta from "../../components/common/PageMeta";
import ComponentCard from "../../components/common/ComponentCard";

export default function Badges() {
  return (
    <div>
      <PageMeta
        title="React.js Badges Dashboard | TailAdmin - React.js Admin Dashboard Template"
        description="This is React.js Badges Dashboard page for TailAdmin - React.js Tailwind CSS Admin Dashboard Template"
      />
      <PageBreadcrumb pageTitle="Badges" />
      <div className="space-y-5 sm:space-y-6">
        <ComponentCard title="With Light Background">
          <div className="flex flex-wrap gap-4 sm:items-center sm:justify-center">
            {/* Light Variant */}
            <Badge color="success">
              Success
            </Badge>{" "}
            <Badge color="error">
              Error
            </Badge>{" "}
            <Badge color="warning">
              Warning
            </Badge>{" "}
            <Badge color="info">
              Info
            </Badge>
          </div>
        </ComponentCard>
        <ComponentCard title="With Solid Background">
          <div className="flex flex-wrap gap-4 sm:items-center sm:justify-center">
            {/* Light Variant */}
            <Badge color="success">
              Success
            </Badge>{" "}
            <Badge color="error">
              Error
            </Badge>{" "}
            <Badge color="warning">
              Warning
            </Badge>{" "}
            <Badge color="info">
              Info
            </Badge>
          </div>
        </ComponentCard>
        <ComponentCard title="Light Background with Left Icon">
          <div className="flex flex-wrap gap-4 sm:items-center sm:justify-center">
            <Badge color="success">
              Success
            </Badge>{" "}
            <Badge color="error">
              Error
            </Badge>{" "}
            <Badge color="warning">
              Warning
            </Badge>{" "}
            <Badge color="info">
              Info
            </Badge>
          </div>
        </ComponentCard>
        <ComponentCard title="Solid Background with Left Icon">
          <div className="flex flex-wrap gap-4 sm:items-center sm:justify-center">
            <Badge color="success">
              Success
            </Badge>{" "}
            <Badge color="error">
              Error
            </Badge>{" "}
            <Badge color="warning">
              Warning
            </Badge>{" "}
            <Badge color="info">
              Info
            </Badge>
          </div>
        </ComponentCard>
        <ComponentCard title="Light Background with Right Icon">
          <div className="flex flex-wrap gap-4 sm:items-center sm:justify-center">
            <Badge color="success">
              Success
            </Badge>{" "}
            <Badge color="error">
              Error
            </Badge>{" "}
            <Badge color="warning">
              Warning
            </Badge>{" "}
            <Badge color="info">
              Info
            </Badge>
          </div>
        </ComponentCard>
        <ComponentCard title="Solid Background with Right Icon">
          <div className="flex flex-wrap gap-4 sm:items-center sm:justify-center">
            <Badge color="success">
              Success
            </Badge>{" "}
            <Badge color="error">
              Error
            </Badge>{" "}
            <Badge color="warning">
              Warning
            </Badge>{" "}
            <Badge color="info">
              Info
            </Badge>
          </div>
        </ComponentCard>
      </div>
    </div>
  );
}

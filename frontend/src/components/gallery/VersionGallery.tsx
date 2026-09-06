import type { VersionDto } from "@/lib/api-client";

export interface VersionGalleryProps {
  versions: VersionDto[];
  baseUrl: string;
}

export function VersionGallery({ versions, baseUrl }: VersionGalleryProps) {
  if (versions.length === 0) {
    return <p className="text-sm text-slate-500">まだバージョンがありません。</p>;
  }

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {versions.map((v) => (
        <figure key={v.id} className="overflow-hidden rounded border border-slate-200">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={`${baseUrl}/${v.thumbnail_path}`}
            alt={`v${v.version_number}`}
            className="h-24 w-full object-cover"
          />
          <figcaption className="bg-slate-100 px-2 py-1 text-xs text-slate-600">
            v{v.version_number}
          </figcaption>
        </figure>
      ))}
    </div>
  );
}

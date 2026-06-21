interface HeaderProps {
  title: string;
  description?: string;
}

export function Header({ title, description }: HeaderProps) {
  return (
    <div className="border-b border-zinc-800 bg-zinc-900 px-8 py-5">
      <h1 className="text-xl font-semibold text-zinc-50">{title}</h1>
      {description && (
        <p className="mt-0.5 text-sm text-zinc-400">{description}</p>
      )}
    </div>
  );
}

import { portraitUrl, type PartnerInfo } from '../api';

interface Props {
  info: PartnerInfo | null;
  variant: 'avatar' | 'hero';
}

export function Portrait({ info, variant }: Props) {
  if (info?.image) {
    return (
      <img className={`portrait portrait-${variant}`} src={portraitUrl(info)} alt={`${info.name}の立ち絵`} />
    );
  }
  return (
    <div className={`portrait portrait-${variant} portrait-empty`} aria-hidden>
      <span>{info?.name.slice(0, 1) ?? ''}</span>
    </div>
  );
}

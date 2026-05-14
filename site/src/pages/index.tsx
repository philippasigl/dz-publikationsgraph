import {useEffect, type ReactNode} from 'react';

export default function Home(): ReactNode {
  // Diese Page wird im standalone-Deploy nicht ausgeliefert (Graph index.html
  // belegt diesen Pfad). Sie wird nur erreicht, wenn React Router intern auf
  // / navigiert. In dem Fall hart neuladen, damit der Server-Graph greift.
  useEffect(() => {
    window.location.replace('/dz-wiki/');
  }, []);

  return null;
}

import path from 'path'
import type { CollectionConfig } from 'payload'
import { isLoggedIn } from '../access/isLoggedIn'

export const Media: CollectionConfig = {
  slug: 'media',
  admin: {
    group: 'Content',
  },
  access: {
    read: isLoggedIn,  // GO-MU-09: was () => true
  },
  upload: {
    staticDir: path.resolve(process.cwd(), '../data/media'),
    mimeTypes: ['image/*'],
    imageSizes: [
      {
        name: 'thumbnail',
        width: 200,
        height: 280,
        position: 'centre',
      },
      {
        name: 'card',
        width: 400,
        height: 560,
        position: 'centre',
      },
    ],
  },
  fields: [
    {
      name: 'alt',
      type: 'text',
    },
  ],
}

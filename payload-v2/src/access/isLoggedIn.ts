/** isLoggedIn — Access control: any authenticated user. */

import type { Access } from 'payload'

export const isLoggedIn: Access = ({ req: { user } }) => {
  return !!user
}

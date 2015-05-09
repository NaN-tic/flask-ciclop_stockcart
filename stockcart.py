from flask import Blueprint, render_template, g, url_for, flash, redirect, \
    session, request
from ciclop.tryton import tryton
from ciclop.csrf import csrf
from ciclop.helpers import login_required
from flask.ext.babel import gettext as _
from trytond.transaction import Transaction

stockcart = Blueprint('stockcart', __name__, template_folder='templates')

User = tryton.pool.get('res.user')
Cart = tryton.pool.get('stock.cart')
ShipmentOutCart = tryton.pool.get('stock.shipment.out.cart')
Location = tryton.pool.get('stock.location')

@stockcart.route("/preferences", methods=["GET", "POST"], endpoint="preferences")
@login_required
@tryton.transaction()
@csrf.exempt
def preferences(lang):
    '''Cart'''
    if request.method == 'POST':
        cart = request.form.get('cart')
        warehouse = request.form.get('warehouse')
        picking = request.form.get('picking')

        data = {}
        if cart:
            data['cart'] = cart
        if warehouse:
            data['stock_warehouse'] = warehouse
        if data:
            user = User(session['user'])
            user.set_preferences(data)
        if picking:
            return redirect(url_for('.picking', lang=g.language))

    carts = Cart.search([])
    warehouses = Location.search([('type', '=', 'warehouse')])

    #breadcumbs
    breadcrumbs = [{
        'slug': None,
        'name': _('Stock'),
        }, {
        'slug': url_for('.preferences', lang=g.language),
        'name': _('Preferences'),
        }]


    return render_template('stock-preferences.html',
        breadcrumbs=breadcrumbs,
        carts=carts,
        warehouses=warehouses,
        )

@stockcart.route("/picking", endpoint="picking")
@login_required
@tryton.transaction(readonly=False)
@csrf.exempt
def picking(lang):
    '''Picking'''

    user = User(session['user'])
    if not user.stock_warehouse:
        flash(_('Select the warehouse in which you are working.'), 'info')
        return redirect(url_for('.preferences', lang=g.language))
    if not user.cart:
        flash(_('Select a cart.'), 'info')
        return redirect(url_for('.preferences', lang=g.language))

    with Transaction().set_user(user.id):
        products = ShipmentOutCart.get_products(warehouse=user.stock_warehouse)

        shipments = []
        if products:
            for k, v in products.iteritems():
                for shipment in v['shipments']:
                    if not shipment['code'] in shipments:
                        shipments.append(shipment['code'])

        # print shipment reports
        ShipmentOutCart.print_shipments(shipments)

    #breadcumbs
    breadcrumbs = [{
        'slug': None,
        'name': _('Stock'),
        }, {
        'slug': url_for('.picking', lang=g.language),
        'name': _('Picking'),
        }]

    return render_template('stock-picking.html',
        breadcrumbs=breadcrumbs,
        products=products,
        shipments=shipments,
        )

@stockcart.route("/picking-done", methods=["POST"], endpoint="picking-done")
@login_required
@tryton.transaction()
@csrf.exempt
def picking_done(lang):
    '''Picking Done'''
    if request.method == 'POST':
        done_end = request.form.get('done-end')
        done_next = request.form.get('done-next')
        shipments = request.form.get('shipments')

        shipments = shipments.split(',')

        ShipmentOutCart.done_cart(shipments)
        if done_next:
            return redirect(url_for('.picking', lang=g.language))

    #breadcumbs
    breadcrumbs = [{
        'slug': None,
        'name': _('Stock'),
        }, {
        'slug': url_for('.picking-done', lang=g.language),
        'name': _('Done'),
        }]

    return render_template('stock-picking-done.html',
        breadcrumbs=breadcrumbs,
        )

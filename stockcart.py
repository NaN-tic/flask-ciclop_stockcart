from flask import Blueprint, render_template, g, url_for, flash, redirect, \
    session, request, jsonify
from ciclop.tryton import tryton
from ciclop.csrf import csrf
from ciclop.helpers import login_required
from flask.ext.babel import gettext as _
from trytond.transaction import Transaction

stockcart = Blueprint('stockcart', __name__, template_folder='templates')

User = tryton.pool.get('res.user')
Cart = tryton.pool.get('stock.cart')
ShipmentOutCart = tryton.pool.get('stock.shipment.out.cart')
ShipmentOut = tryton.pool.get('stock.shipment.out')
Location = tryton.pool.get('stock.location')

@stockcart.route("/print", methods=["POST"], endpoint="print")
@login_required
@tryton.transaction()
@csrf.exempt
def print_shipments(lang):
    '''Print Shipments - Get JSON shipments codes'''

    shipments = request.json.get('shipments')
    if shipments:
        user = User(session['user'])
        with Transaction().set_user(user.id):
            ShipmentOutCart.print_shipments(shipments)

    return jsonify(result=True)

@stockcart.route("/preferences", methods=["GET", "POST"], endpoint="preferences")
@login_required
@tryton.transaction()
@csrf.exempt
def preferences(lang):
    '''Cart'''
    if request.method == 'POST':
        user = User(session['user'])

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
            with Transaction().set_user(user.id):
                user.set_preferences(data)
        if picking:
            return redirect(url_for('.picking', lang=g.language))
        flash(_('Updated your prefrences'))

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

@stockcart.route("/picking", methods=["GET", "POST"], endpoint="picking")
@login_required
@tryton.transaction(readonly=False)
@csrf.exempt
def picking(lang):
    '''Picking'''

    if not session.get('stock_warehouse') or not session.get('cart'):
        flash(_('Select the warehouse or the cart in which you are working.'), 'info')
        return redirect(url_for('.preferences', lang=g.language))

    user_id = session['user']
    warehouse = session['stock_warehouse']

    #breadcumbs
    breadcrumbs = [{
        'slug': None,
        'name': _('Stock'),
        }, {
        'slug': url_for('.picking', lang=g.language),
        'name': _('Picking'),
        }]

    if request.form.get('picking'):
        if request.form.getlist('shipments'): # picking with select shipments
            shipments_request = filter(None, set(request.form.getlist('shipments'))) # remove empty str

            shipments = ShipmentOut.search([
                ('state', '=', 'assigned'),
                ('code', 'in', shipments_request),
                ])
            if shipments:
                carts_assigned = ShipmentOutCart.search([
                    ('shipment', 'in', shipments),
                    ])
                shipments_assigned = [c.shipment for c in carts_assigned]

                to_create = []
                for s in shipments:
                    if s not in shipments_assigned:
                        to_create.append({'shipment': s})
                    if s.code not in shipments_request:
                        shipments_request.remove(s.code)

                if to_create:
                    carts = ShipmentOutCart.create(to_create)
                else:
                    carts = []

                products = ShipmentOutCart.get_products_by_carts(carts_assigned + carts)

                return render_template('stock-picking.html',
                    breadcrumbs=breadcrumbs,
                    products=products,
                    shipments=shipments_request, # code shipments
                    )
            else:
                flash(_('There are not found shipments with code and state assigned.'), 'info')
        else: # picking with assign shipments
            with Transaction().set_user(user_id):
                products = ShipmentOutCart.get_products(warehouse=warehouse)

                shipments = []
                for product in products:
                    for k, v in product.iteritems():
                        for shipment in v['shipments']:
                            if not shipment['code'] in shipments:
                                shipments.append(shipment['code'])
                shipments = sorted(shipments)

            return render_template('stock-picking.html',
                breadcrumbs=breadcrumbs,
                products=products,
                shipments=shipments, # code shipments
                )

    return render_template('stock-picking-index.html',
        breadcrumbs=breadcrumbs,
        )

@stockcart.route("/picking-done", methods=["POST"], endpoint="picking-done")
@login_required
@tryton.transaction()
@csrf.exempt
def picking_done(lang):
    '''Picking Done'''
    if request.method == 'POST':
        shipments = request.form.get('shipments')

        shipments = shipments.split(',')

        ShipmentOutCart.done_cart(shipments)
        flash(_('Picked {total} shipments: {shipments}.').format(
            total=len(shipments),
            shipments=', '.join(shipments)),
            'info')

    return redirect(url_for('.picking', lang=g.language))
